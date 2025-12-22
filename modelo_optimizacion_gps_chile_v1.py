# modelo_optimizacion_gps_chile_v6_FINAL_opcionA.py
# Opción A (CORRECCIÓN OPERATIVA):
# - El viaje compite contra la jornada completa H_DIA (no contra horas_diarias(tecnico)).
# - Si tv (horas de viaje) > H_DIA: ese día es SOLO de viaje (0 instalación),
#   duerme en destino y al día siguiente recién puede instalar.
# - Si tv <= H_DIA: ese día puede viajar + instalar (instala hasta min(horas_instal_disponibles, horas_pendientes)).
#
# Mantiene:
# - Todo input en UF (NO se divide por UF).
# - PxQ es UF POR GPS (se multiplica por GPS externos).
# - Materiales incluidos (1 vez por ciudad).
# - Santiago mixto (asigna horas internas hasta capacidad y el resto PxQ externo).
# - Auditoría: si tv>0 entonces viaje_uf>0 (origen != destino).
#
# Requiere: pandas, numpy, openpyxl
# Inputs: ./data/
# Output: outputs/resultado_optimizacion_gps_v6.xlsx

import os
import math
from datetime import time as dt_time
from copy import deepcopy

import numpy as np
import pandas as pd

# =========================
# 0. CONFIG
# =========================
PATH = "data/"
OUTPUTS_DIR = "outputs"
SANTIAGO = "Santiago"
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# =========================
# 1. PARSEO ROBUSTO NUMÉRICO (CL)
# =========================
def _parse_cl_number(s: str) -> float:
    s = str(s).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return np.nan
    s = s.replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "")
        s = s.replace(",", ".")
        return float(s)
    if "," in s and "." not in s:
        s = s.replace(",", ".")
        return float(s)
    return float(s)

def time_to_hours(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return 0.0
    if isinstance(x, dt_time):
        return x.hour + x.minute / 60.0 + x.second / 3600.0
    if isinstance(x, str) and ":" in x:
        parts = x.strip().split(":")
        hh = float(parts[0])
        mm = float(parts[1])
        ss = float(parts[2]) if len(parts) >= 3 else 0.0
        return hh + mm / 60.0 + ss / 3600.0
    return float(x)

def safe_float(x, default=0.0):
    try:
        if x is None:
            return default
        if isinstance(x, float) and np.isnan(x):
            return default
        if isinstance(x, dt_time):
            return time_to_hours(x)
        if isinstance(x, (int, float, np.integer, np.floating)):
            return float(x)
        return float(_parse_cl_number(x))
    except Exception:
        return default

def norm_city(x):
    if pd.isna(x):
        return x
    return str(x).strip()

def normalize_matrix(df: pd.DataFrame) -> pd.DataFrame:
    df.index = df.index.map(norm_city)
    df.columns = df.columns.map(norm_city)
    return df

def check_matrix_coverage(name: str, df: pd.DataFrame, cities: list[str]):
    missing_rows = [c for c in cities if c not in df.index]
    missing_cols = [c for c in cities if c not in df.columns]
    if missing_rows or missing_cols:
        raise ValueError(f"Matriz {name} no cubre todas las ciudades. Faltan filas={missing_rows}, cols={missing_cols}")

def coerce_matrix_to_float(df: pd.DataFrame, name: str) -> pd.DataFrame:
    out = df.copy()
    out = out.applymap(lambda v: safe_float(v, default=np.nan))
    n_nan = int(np.isnan(out.values).sum())
    if n_nan > 0:
        print(f"[WARN] Matriz {name}: quedaron {n_nan} celdas NaN tras parseo. Revisa input.")
    return out

# =========================
# 2. CARGA DE DATOS
# =========================
demanda = pd.read_excel(os.path.join(PATH, "demanda_ciudades.xlsx"))
internos = pd.read_excel(os.path.join(PATH, "tecnicos_internos.xlsx"))
pxq = pd.read_excel(os.path.join(PATH, "costos_externos.xlsx"))
flete = pd.read_excel(os.path.join(PATH, "flete_ciudad.xlsx"))
kits = pd.read_excel(os.path.join(PATH, "materiales.xlsx"))
param_df = pd.read_excel(os.path.join(PATH, "parametros.xlsx"))

km = pd.read_excel(os.path.join(PATH, "matriz_distancia_km.xlsx"), index_col=0)
peajes = pd.read_excel(os.path.join(PATH, "matriz_peajes.xlsx"), index_col=0)
avion_cost = pd.read_excel(os.path.join(PATH, "matriz_costo_avion.xlsx"), index_col=0)
avion_time = pd.read_excel(os.path.join(PATH, "matriz_tiempo_avion.xlsx"), index_col=0)

# =========================
# 3. NORMALIZACIÓN + COERCIÓN
# =========================
demanda["ciudad"] = demanda["ciudad"].apply(norm_city)
CIUDADES = demanda["ciudad"].tolist()

km = normalize_matrix(km)
peajes = normalize_matrix(peajes)
avion_cost = normalize_matrix(avion_cost)
avion_time = normalize_matrix(avion_time)

check_matrix_coverage("km", km, CIUDADES)
check_matrix_coverage("peajes", peajes, CIUDADES)
check_matrix_coverage("avion_cost", avion_cost, CIUDADES)
check_matrix_coverage("avion_time", avion_time, CIUDADES)

km = coerce_matrix_to_float(km, "km")
peajes = coerce_matrix_to_float(peajes, "peajes")
avion_cost = coerce_matrix_to_float(avion_cost, "avion_cost")
# avion_time lo dejamos “mixto” (HH:MM:SS o num). Se parsea en t_viaje.

internos["tecnico"] = internos["tecnico"].apply(norm_city)
internos["ciudad_base"] = internos["ciudad_base"].apply(norm_city)

TECNICOS = internos["tecnico"].tolist()
MODOS = ["terrestre", "avion"]

# =========================
# 4. PARÁMETROS / DEMANDA
# =========================
param = param_df.set_index("parametro")["valor"].to_dict()

PRECIO_BENCINA_UF_KM = safe_float(param.get("precio_bencina"), 0.03)  # UF/km
ALOJ_UF = safe_float(param.get("alojamiento_uf_noche"), 1.1)
ALMU_UF = safe_float(param.get("almuerzo_uf_dia"), 0.5)
INCENTIVO_UF = safe_float(param.get("incentivo_por_gps"), 1.12)
H_DIA = safe_float(param.get("horas_jornada"), 7.0)  # jornada completa para viaje + trabajo
VEL = safe_float(param.get("velocidad_terrestre"), 80.0)
TIEMPO_INST_GPS_H = safe_float(param.get("tiempo_instalacion_gps"), 0.75)

DIAS_SEM = int(safe_float(param.get("dias_semana"), 6))
SEMANAS = int(safe_float(param.get("semanas_proyecto"), 4))
DIAS_MAX = DIAS_SEM * SEMANAS
HH_MES = safe_float(param.get("hh_mes"), 180.0)

demanda["vehiculos_1gps"] = demanda["vehiculos_1gps"].apply(lambda v: safe_float(v, 0.0))
demanda["vehiculos_2gps"] = demanda["vehiculos_2gps"].apply(lambda v: safe_float(v, 0.0))
demanda["gps_total"] = demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]
demanda["horas"] = TIEMPO_INST_GPS_H * demanda["gps_total"]

H = dict(zip(demanda["ciudad"], demanda["horas"]))
GPS_TOTAL = dict(zip(demanda["ciudad"], demanda["gps_total"]))
VEH1 = dict(zip(demanda["ciudad"], demanda["vehiculos_1gps"]))
VEH2 = dict(zip(demanda["ciudad"], demanda["vehiculos_2gps"]))

# Materiales (UF)
kits["tipo_kit"] = kits["tipo_kit"].astype(str).str.strip()
KIT1 = safe_float(kits.loc[kits["tipo_kit"] == "1_GPS", "costo"].values[0], 0.0)
KIT2 = safe_float(kits.loc[kits["tipo_kit"] == "2_GPS", "costo"].values[0], 0.0)
MATERIAL_UF = {c: safe_float(VEH1.get(c, 0), 0) * KIT1 + safe_float(VEH2.get(c, 0), 0) * KIT2 for c in CIUDADES}

# PXQ y flete (UF)
pxq["ciudad"] = pxq["ciudad"].apply(norm_city)
flete["ciudad"] = flete["ciudad"].apply(norm_city)
pxq["pxq_externo"] = pxq["pxq_externo"].apply(lambda v: safe_float(v, 0.0))
flete["costo_flete"] = flete["costo_flete"].apply(lambda v: safe_float(v, 0.0))

PXQ_UF_POR_GPS = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))  # UF/GPS
FLETE_UF = dict(zip(flete["ciudad"], flete["costo_flete"]))     # UF

# =========================
# 5. FUNCIONES BASE
# =========================
def base_tecnico(tecnico: str) -> str:
    return internos.loc[internos["tecnico"] == tecnico, "ciudad_base"].values[0]

def hh_semana(tecnico: str) -> float:
    v = safe_float(internos.loc[internos["tecnico"] == tecnico, "hh_semana_proyecto"].values[0], 0.0)
    # si viene como FTE (0-1), convertir a horas/semana reales
    if v <= 1.5:
        return v * (DIAS_SEM * H_DIA)
    return v

def alpha_tecnico(tecnico: str) -> float:
    return hh_semana(tecnico) / max(1e-9, DIAS_SEM * H_DIA)

def horas_diarias_instal(tecnico: str) -> float:
    # capacidad “productiva” de instalación (FTE)
    return H_DIA * alpha_tecnico(tecnico)

def t_viaje(ciudad_origen: str, ciudad_destino: str, modo: str) -> float:
    if ciudad_origen == ciudad_destino:
        return 0.0
    if modo == "terrestre":
        dist = safe_float(km.loc[ciudad_origen, ciudad_destino], default=np.nan)
        if np.isnan(dist):
            raise RuntimeError(f"[DATA] km faltante para {ciudad_origen} -> {ciudad_destino}")
        return dist / max(1e-9, VEL)

    v = avion_time.loc[ciudad_origen, ciudad_destino]
    if isinstance(v, dt_time) or (isinstance(v, str) and ":" in str(v)):
        tv = time_to_hours(v)
    else:
        tv = safe_float(v, default=np.nan)
    if np.isnan(tv):
        raise RuntimeError(f"[DATA] avion_time faltante para {ciudad_origen} -> {ciudad_destino}")
    return tv

def costo_viaje_uf(ciudad_origen: str, ciudad_destino: str, modo: str) -> float:
    if ciudad_origen == ciudad_destino:
        return 0.0
    if modo == "terrestre":
        dist_km = safe_float(km.loc[ciudad_origen, ciudad_destino], default=np.nan)
        peaje_uf = safe_float(peajes.loc[ciudad_origen, ciudad_destino], default=np.nan)
        if np.isnan(dist_km):
            raise RuntimeError(f"[DATA] km faltante para {ciudad_origen} -> {ciudad_destino}")
        if np.isnan(peaje_uf):
            raise RuntimeError(f"[DATA] peajes faltante para {ciudad_origen} -> {ciudad_destino}")
        return dist_km * PRECIO_BENCINA_UF_KM + peaje_uf

    c = safe_float(avion_cost.loc[ciudad_origen, ciudad_destino], default=np.nan)
    if np.isnan(c):
        raise RuntimeError(f"[DATA] avion_cost faltante para {ciudad_origen} -> {ciudad_destino}")
    return c

def dias_ciudad_aprox(ciudad: str, tecnico: str, modo: str, origen: str) -> int:
    """
    Aproximación para heurística (no simulación final):
    - Día 1: si tv < H_DIA, queda algo de jornada para instalar (pero limitado por capacidad de instalación hd_inst).
    - Siguientes días: instala hd_inst completos.
    """
    tv = t_viaje(origen, ciudad, modo)
    hd_inst = horas_diarias_instal(tecnico)

    # si viaje se come el día -> 1 día viaje + días de instalación completos
    if tv >= H_DIA - 1e-9:
        return 1 + int(math.ceil(H[ciudad] / max(1e-9, hd_inst)))

    # si alcanza a instalar algo el día 1
    h_inst_day1 = min(hd_inst, max(0.0, H_DIA - tv))
    rem = max(0.0, H[ciudad] - h_inst_day1)
    if rem <= 1e-9:
        return 1
    return 1 + int(math.ceil(rem / max(1e-9, hd_inst)))

def costo_sueldo_proyecto_uf(tecnico: str) -> float:
    sueldo_mes = safe_float(internos.loc[internos["tecnico"] == tecnico, "sueldo_uf"].values[0], 0.0)
    hh_proy = hh_semana(tecnico) * SEMANAS
    return sueldo_mes * (hh_proy / max(1e-9, HH_MES))

def costo_externo_ciudad(ciudad: str, gps_externo: float | None = None) -> float:
    gps_use = safe_float(GPS_TOTAL.get(ciudad, 0.0), 0.0) if gps_externo is None else safe_float(gps_externo, 0.0)
    pxq_total = safe_float(PXQ_UF_POR_GPS.get(ciudad, 0.0), 0.0) * gps_use
    return pxq_total + safe_float(FLETE_UF.get(ciudad, 0.0), 0.0) + safe_float(MATERIAL_UF.get(ciudad, 0.0), 0.0)

def costo_interno_aprox_base_a_ciudad(ciudad: str, tecnico: str, modo: str) -> float:
    """
    Costo aproximado para heurística (no la simulación final).
    """
    base = base_tecnico(tecnico)
    dias = dias_ciudad_aprox(ciudad, tecnico, modo, origen=base)

    costo = 0.0
    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    costo += sueldo_proy * (dias / max(1e-9, DIAS_MAX))

    if ciudad != base:
        costo += dias * ALOJ_UF

    costo += dias * ALMU_UF
    costo += INCENTIVO_UF * GPS_TOTAL[ciudad]
    costo += costo_viaje_uf(base, ciudad, modo)

    # flete: no aplica si base Santiago y llega terrestre
    if base != SANTIAGO or modo == "avion":
        costo += safe_float(FLETE_UF.get(ciudad, 0.0), 0.0)

    costo += safe_float(MATERIAL_UF.get(ciudad, 0.0), 0.0)
    return costo

# =========================
# 6. SIMULACIÓN REGIONES (Opción A)
# =========================
def simulate_tech_schedule_regiones(tecnico, cities_list):
    base = base_tecnico(tecnico)
    hd_inst = horas_diarias_instal(tecnico)

    day = 1
    sleep_city = base

    plan = []
    cost = {
        "travel_uf": 0.0,
        "aloj_uf": 0.0,
        "alm_uf": 0.0,
        "inc_uf": 0.0,
        "sueldo_uf": 0.0,
        "flete_uf": 0.0,
        "material_uf": 0.0,
    }

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1e-9, DIAS_MAX)

    pending_h = {c: H[c] for c in cities_list}
    added_material = set()

    def flete_aplica(ciudad, modo_llegada):
        # regla: solo NO aplica si base Santiago y llega terrestre
        if base != SANTIAGO:
            return True
        return modo_llegada == "avion"

    for c in cities_list:
        if day > DIAS_MAX:
            break

        # cobrar materiales 1 vez por ciudad
        if c not in added_material:
            cost["material_uf"] += safe_float(MATERIAL_UF.get(c, 0.0), 0.0)
            added_material.add(c)

        if pending_h[c] <= 1e-9:
            continue

        # elegir modo más barato desde donde durmió
        road_cost = costo_viaje_uf(sleep_city, c, "terrestre")
        air_cost = costo_viaje_uf(sleep_city, c, "avion")
        modo_in = "avion" if air_cost < road_cost else "terrestre"

        tv = t_viaje(sleep_city, c, modo_in)
        cv = costo_viaje_uf(sleep_city, c, modo_in)

        # auditoría dura costo viaje
        if sleep_city != c and tv > 1e-9 and cv <= 1e-9:
            raise RuntimeError(
                f"[AUDIT] Viaje con tiempo>0 pero costo=0. Tec={tecnico}, dia={day}, {sleep_city}->{c}, modo={modo_in}, tv={tv}"
            )

        # costos del día (viaje siempre se cobra el día que ocurre)
        cost["travel_uf"] += cv
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia

        flete_day = safe_float(FLETE_UF.get(c, 0.0), 0.0) if flete_aplica(c, modo_in) else 0.0
        cost["flete_uf"] += flete_day

        # ===== OPCIÓN A: si tv > H_DIA -> día completo de viaje (0 instalación) =====
        if tv > H_DIA + 1e-9:
            sleep_city = c
            aloj_day = ALOJ_UF if sleep_city != base else 0.0
            cost["aloj_uf"] += aloj_day

            plan.append({
                "tecnico": tecnico,
                "dia": day,
                "ciudad_trabajo": c,
                "horas_instal": 0.0,
                "gps_inst": 0.0,
                "viaje_modo_manana": modo_in,
                "viaje_h_manana": tv,
                "duerme_en": sleep_city,
                "viaje_uf": cv,
                "aloj_uf": aloj_day,
                "alm_uf": ALMU_UF,
                "sueldo_uf": sueldo_dia,
                "inc_uf": 0.0,
                "flete_uf": flete_day,
                "material_uf": 0.0,
                "nota": "DIA_SOLO_VIAJE (tv>H_DIA)"
            })
            day += 1
            # al día siguiente recién puede instalar
            continue

        # si tv <= H_DIA, queda tiempo de jornada para instalar,
        # pero la instalación está limitada por capacidad productiva hd_inst
        time_for_work = max(0.0, H_DIA - tv)
        inst_cap_today = min(hd_inst, time_for_work)

        installed = min(pending_h[c], inst_cap_today)
        pending_h[c] -= installed
        gps_inst = installed / max(1e-9, TIEMPO_INST_GPS_H)
        inc_day = INCENTIVO_UF * gps_inst
        cost["inc_uf"] += inc_day

        sleep_city = c
        aloj_day = ALOJ_UF if sleep_city != base else 0.0
        cost["aloj_uf"] += aloj_day

        plan.append({
            "tecnico": tecnico,
            "dia": day,
            "ciudad_trabajo": c,
            "horas_instal": installed,
            "gps_inst": gps_inst,
            "viaje_modo_manana": modo_in,
            "viaje_h_manana": tv,
            "duerme_en": sleep_city,
            "viaje_uf": cv,
            "aloj_uf": aloj_day,
            "alm_uf": ALMU_UF,
            "sueldo_uf": sueldo_dia,
            "inc_uf": inc_day,
            "flete_uf": flete_day,
            "material_uf": 0.0,
            "nota": ""
        })
        day += 1

        # seguir en la misma ciudad hasta terminar (días sin viaje)
        while pending_h[c] > 1e-9 and day <= DIAS_MAX:
            installed = min(pending_h[c], hd_inst)
            pending_h[c] -= installed
            gps_inst = installed / max(1e-9, TIEMPO_INST_GPS_H)
            inc_day = INCENTIVO_UF * gps_inst

            cost["inc_uf"] += inc_day
            cost["alm_uf"] += ALMU_UF
            cost["sueldo_uf"] += sueldo_dia

            aloj_day = ALOJ_UF if sleep_city != base else 0.0
            cost["aloj_uf"] += aloj_day

            plan.append({
                "tecnico": tecnico,
                "dia": day,
                "ciudad_trabajo": c,
                "horas_instal": installed,
                "gps_inst": gps_inst,
                "viaje_modo_manana": None,
                "viaje_h_manana": 0.0,
                "duerme_en": sleep_city,
                "viaje_uf": 0.0,
                "aloj_uf": aloj_day,
                "alm_uf": ALMU_UF,
                "sueldo_uf": sueldo_dia,
                "inc_uf": inc_day,
                "flete_uf": 0.0,
                "material_uf": 0.0,
                "nota": ""
            })
            day += 1

    complete = all(hh <= 1e-6 for hh in pending_h.values())
    feasible = (day - 1) <= DIAS_MAX and complete
    last_day = day - 1
    return plan, cost, feasible, last_day, pending_h

# =========================
# 7. SANTIAGO MIXTO (instalación sin viaje)
# =========================
def simulate_santiago_for_tecnico(tecnico: str, horas_scl: float, start_day: int):
    if horas_scl <= 1e-9:
        return [], {"alm_uf": 0.0, "sueldo_uf": 0.0, "inc_uf": 0.0}, 0.0, 0, start_day - 1

    base = base_tecnico(tecnico)
    hd_inst = horas_diarias_instal(tecnico)

    day = start_day
    plan = []
    cost = {"alm_uf": 0.0, "sueldo_uf": 0.0, "inc_uf": 0.0}

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1e-9, DIAS_MAX)

    remaining = horas_scl
    horas_instaladas = 0.0
    dias_usados = 0

    while remaining > 1e-9 and day <= DIAS_MAX:
        installed = min(remaining, hd_inst)
        remaining -= installed
        horas_instaladas += installed
        dias_usados += 1

        gps_inst = installed / max(1e-9, TIEMPO_INST_GPS_H)
        inc_day = INCENTIVO_UF * gps_inst

        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia
        cost["inc_uf"] += inc_day

        plan.append({
            "tecnico": tecnico,
            "dia": day,
            "ciudad_trabajo": SANTIAGO,
            "horas_instal": installed,
            "gps_inst": gps_inst,
            "viaje_modo_manana": None,
            "viaje_h_manana": 0.0,
            "duerme_en": base,
            "viaje_uf": 0.0,
            "aloj_uf": 0.0,
            "alm_uf": ALMU_UF,
            "sueldo_uf": sueldo_dia,
            "inc_uf": inc_day,
            "flete_uf": 0.0,
            "material_uf": 0.0,
            "nota": ""
        })
        day += 1

    end_day = day - 1
    return plan, cost, horas_instaladas, dias_usados, end_day

# =========================
# 8. HEURÍSTICA (greedy + mejora) + asignación Santiago mixto
# =========================
def total_all_external():
    return sum(costo_externo_ciudad(c) for c in CIUDADES)

def greedy_initial_regiones():
    city_type = {c: ("mixto_scl" if c == SANTIAGO else "externo") for c in CIUDADES}
    tech_cities = {t: [] for t in TECNICOS}
    used_days = {t: 0 for t in TECNICOS}

    candidates = []
    for c in CIUDADES:
        if c == SANTIAGO:
            continue
        ext = costo_externo_ciudad(c)

        best = None
        for t in TECNICOS:
            base = base_tecnico(t)
            for mo in MODOS:
                dias = dias_ciudad_aprox(c, t, mo, origen=base)
                if dias > DIAS_MAX:
                    continue
                intc = costo_interno_aprox_base_a_ciudad(c, t, mo)
                if best is None or intc < best[0]:
                    best = (intc, t, mo, dias)

        if best is None:
            continue

        saving = ext - best[0]
        if saving > 1e-6:
            candidates.append((saving, c, best))

    candidates.sort(reverse=True, key=lambda x: x[0])

    for saving, c, (intc, t, mo, dias) in candidates:
        if used_days[t] + dias <= DIAS_MAX:
            city_type[c] = "interno"
            tech_cities[t].append(c)
            used_days[t] += dias

    return city_type, tech_cities

def allocate_santiago_mix(tech_cities, prefer_base_scl=True):
    scl_hours_total = safe_float(H.get(SANTIAGO, 0.0), 0.0)
    if scl_hours_total <= 1e-9:
        return {t: 0.0 for t in TECNICOS}, 0.0

    tech_last_day = {}
    for t in TECNICOS:
        _, _, feas, last_day, _ = simulate_tech_schedule_regiones(t, tech_cities.get(t, []))
        tech_last_day[t] = (last_day if feas else DIAS_MAX)

    tech_capacity_hours = {}
    for t in TECNICOS:
        hd_inst = horas_diarias_instal(t)
        days_left = max(0, DIAS_MAX - tech_last_day[t])
        tech_capacity_hours[t] = days_left * hd_inst

    tech_order = list(TECNICOS)
    if prefer_base_scl:
        tech_order.sort(key=lambda t: 0 if base_tecnico(t) == SANTIAGO else 1)

    santiago_hours_by_tech = {t: 0.0 for t in TECNICOS}
    remaining = scl_hours_total

    for t in tech_order:
        if remaining <= 1e-9:
            break
        cap = tech_capacity_hours.get(t, 0.0)
        if cap <= 1e-9:
            continue
        take = min(remaining, cap)
        santiago_hours_by_tech[t] = take
        remaining -= take

    internal_total = scl_hours_total - remaining
    return santiago_hours_by_tech, internal_total

def total_cost_solution(city_type, tech_cities, santiago_internal_hours_by_tech):
    total = 0.0

    for t, clist in tech_cities.items():
        _, cst_reg, feas_reg, last_day, _ = simulate_tech_schedule_regiones(t, clist)
        if not feas_reg:
            return 1e18
        total += sum(cst_reg.values())

        hscl = safe_float(santiago_internal_hours_by_tech.get(t, 0.0), 0.0)
        if hscl > 1e-9:
            _, cst_scl, h_inst, _, _ = simulate_santiago_for_tecnico(t, hscl, start_day=last_day + 1)
            if h_inst + 1e-6 < hscl:
                return 1e18
            total += (cst_scl["alm_uf"] + cst_scl["sueldo_uf"] + cst_scl["inc_uf"])

    # externos (incluye Santiago externo si faltó capacidad)
    for c in CIUDADES:
        if c == SANTIAGO:
            total += safe_float(MATERIAL_UF.get(c, 0.0), 0.0)
            total += safe_float(FLETE_UF.get(c, 0.0), 0.0)
        elif city_type.get(c) == "externo":
            total += costo_externo_ciudad(c)

    return total

def improve_solution_regiones(city_type, tech_cities, iters=1200, seed=7):
    best_ct = deepcopy(city_type)
    best_tc = deepcopy(tech_cities)

    best_scl_hours_by_tech, _ = allocate_santiago_mix(best_tc, prefer_base_scl=True)
    best_cost = total_cost_solution(best_ct, best_tc, best_scl_hours_by_tech)

    rng = np.random.default_rng(seed)
    cities_no_scl = [c for c in CIUDADES if c != SANTIAGO]

    for _ in range(iters):
        ct2 = deepcopy(best_ct)
        tc2 = deepcopy(best_tc)

        move_type = int(rng.integers(0, 2))  # 0 flip, 1 reassign

        if move_type == 0:
            c = str(rng.choice(cities_no_scl))
            if ct2.get(c) == "interno":
                ct2[c] = "externo"
                for t in TECNICOS:
                    if c in tc2[t]:
                        tc2[t].remove(c)
            else:
                best_t = None
                best_proxy = 1e18
                for t in TECNICOS:
                    if c in tc2[t]:
                        continue
                    # quick feasibility test with simulation
                    trial = tc2[t] + [c]
                    _, _, feas, _, _ = simulate_tech_schedule_regiones(t, trial)
                    if not feas:
                        continue
                    proxy = min(costo_interno_aprox_base_a_ciudad(c, t, mo) for mo in MODOS)
                    if proxy < best_proxy:
                        best_proxy = proxy
                        best_t = t
                if best_t is None:
                    continue
                ct2[c] = "interno"
                tc2[best_t].append(c)

        else:
            donors = [t for t in TECNICOS if len(tc2[t]) > 0]
            if not donors:
                continue
            t_from = str(rng.choice(donors))
            c = str(rng.choice(tc2[t_from]))
            t_to = str(rng.choice([t for t in TECNICOS if t != t_from]))

            tc2[t_from].remove(c)
            tc2[t_to].append(c)

        scl_hours_by_tech2, _ = allocate_santiago_mix(tc2, prefer_base_scl=True)
        new_cost = total_cost_solution(ct2, tc2, scl_hours_by_tech2)

        if new_cost + 1e-6 < best_cost:
            best_cost = new_cost
            best_ct = ct2
            best_tc = tc2
            best_scl_hours_by_tech = scl_hours_by_tech2

    return best_ct, best_tc, best_scl_hours_by_tech, best_cost

# =========================
# 9. RUN + EXPORT
# =========================
def run_all():
    ct0, tc0 = greedy_initial_regiones()
    ct, tc, scl_hours_by_tech, _ = improve_solution_regiones(ct0, tc0)

    plan_rows = []
    tech_cost_rows = []
    city_resp = {}

    for t in TECNICOS:
        clist = tc.get(t, [])
        plan_reg, cst_reg, feas_reg, last_day, _ = simulate_tech_schedule_regiones(t, clist)
        if not feas_reg:
            raise RuntimeError(f"Solución infeasible en regiones para técnico {t}.")

        for c in clist:
            city_resp[c] = t

        plan_rows.extend(plan_reg)

        hscl = safe_float(scl_hours_by_tech.get(t, 0.0), 0.0)
        plan_scl = []
        cst_scl = {"alm_uf": 0.0, "sueldo_uf": 0.0, "inc_uf": 0.0}
        if hscl > 1e-9:
            plan_scl, cst_scl, h_inst, _, _ = simulate_santiago_for_tecnico(t, hscl, start_day=last_day + 1)
            if h_inst + 1e-6 < hscl:
                raise RuntimeError(f"Santiago mixto infeasible para técnico {t}.")
            plan_rows.extend(plan_scl)

        cst_total = {
            "travel_uf": cst_reg["travel_uf"],
            "aloj_uf": cst_reg["aloj_uf"],
            "alm_uf": cst_reg["alm_uf"] + cst_scl["alm_uf"],
            "inc_uf": cst_reg["inc_uf"] + cst_scl["inc_uf"],
            "sueldo_uf": cst_reg["sueldo_uf"] + cst_scl["sueldo_uf"],
            "flete_uf": cst_reg["flete_uf"],
            "material_uf": cst_reg["material_uf"],
        }
        tech_cost_rows.append({
            "responsable": t,
            "tipo": "INTERNO",
            **cst_total,
            "total_uf": sum(cst_total.values()),
            "ciudades_regiones": ", ".join(clist),
            "santiago_horas_asignadas": hscl
        })

    df_plan = pd.DataFrame(plan_rows)
    if not df_plan.empty:
        df_plan = df_plan.sort_values(["tecnico", "dia"])

    # agregación por ciudad (desde plan)
    if not df_plan.empty:
        agg = df_plan.groupby("ciudad_trabajo")[[
            "viaje_uf","aloj_uf","alm_uf","inc_uf","sueldo_uf","flete_uf","horas_instal","gps_inst"
        ]].sum().reset_index()
        agg_map = {r["ciudad_trabajo"]: r for _, r in agg.iterrows()}
    else:
        agg_map = {}

    # costos por ciudad
    city_rows = []
    santiago_gps_total = safe_float(GPS_TOTAL.get(SANTIAGO, 0.0), 0.0)
    santiago_horas_total = safe_float(H.get(SANTIAGO, 0.0), 0.0)

    santiago_inst_h = float(agg_map[SANTIAGO]["horas_instal"]) if SANTIAGO in agg_map else 0.0
    santiago_inst_gps = float(agg_map[SANTIAGO]["gps_inst"]) if SANTIAGO in agg_map else 0.0

    santiago_gps_ext = max(0.0, santiago_gps_total - santiago_inst_gps)
    santiago_pxq_ext = safe_float(PXQ_UF_POR_GPS.get(SANTIAGO, 0.0), 0.0) * santiago_gps_ext

    for c in CIUDADES:
        if c == SANTIAGO:
            r = agg_map.get(c, None)
            viaje = float(r["viaje_uf"]) if r is not None else 0.0
            aloj = float(r["aloj_uf"]) if r is not None else 0.0
            alm = float(r["alm_uf"]) if r is not None else 0.0
            inc = float(r["inc_uf"]) if r is not None else 0.0
            sueldo = float(r["sueldo_uf"]) if r is not None else 0.0

            flete_city = safe_float(FLETE_UF.get(c, 0.0), 0.0)  # tú lo dejaste en 0
            mat_city = safe_float(MATERIAL_UF.get(c, 0.0), 0.0)

            total_city = viaje + aloj + alm + inc + sueldo + flete_city + mat_city + santiago_pxq_ext

            city_rows.append({
                "ciudad": c,
                "tipo_final": "mixto_scl",
                "responsable": "MIXTO",
                "viaje_uf": viaje,
                "aloj_uf": aloj,
                "alm_uf": alm,
                "inc_uf": inc,
                "sueldo_uf": sueldo,
                "flete_uf": flete_city,
                "pxq_total_uf": santiago_pxq_ext,
                "material_uf": mat_city,
                "total_uf": total_city,
                "gps_total": santiago_gps_total,
                "horas_instal_total": santiago_horas_total,
                "horas_instal_sim": santiago_inst_h,
                "gps_inst_sim": santiago_inst_gps,
                "gps_externo": santiago_gps_ext,
            })
            continue

        if c in city_resp:
            r = agg_map.get(c)
            mat_city = safe_float(MATERIAL_UF.get(c, 0.0), 0.0)
            row = {
                "ciudad": c,
                "tipo_final": "interno",
                "responsable": city_resp[c],
                "viaje_uf": float(r["viaje_uf"]),
                "aloj_uf": float(r["aloj_uf"]),
                "alm_uf": float(r["alm_uf"]),
                "inc_uf": float(r["inc_uf"]),
                "sueldo_uf": float(r["sueldo_uf"]),
                "flete_uf": float(r["flete_uf"]),
                "pxq_total_uf": 0.0,
                "material_uf": mat_city,
                "gps_total": safe_float(GPS_TOTAL.get(c, 0.0), 0.0),
                "horas_instal_total": safe_float(H.get(c, 0.0), 0.0),
                "horas_instal_sim": float(r["horas_instal"]),
                "gps_inst_sim": float(r["gps_inst"]),
            }
            row["total_uf"] = (
                row["viaje_uf"] + row["aloj_uf"] + row["alm_uf"] + row["inc_uf"] +
                row["sueldo_uf"] + row["flete_uf"] + row["material_uf"]
            )
            city_rows.append(row)
        else:
            gps_use = safe_float(GPS_TOTAL.get(c, 0.0), 0.0)
            pxq_total = safe_float(PXQ_UF_POR_GPS.get(c, 0.0), 0.0) * gps_use
            mat_city = safe_float(MATERIAL_UF.get(c, 0.0), 0.0)
            flete_city = safe_float(FLETE_UF.get(c, 0.0), 0.0)
            city_rows.append({
                "ciudad": c,
                "tipo_final": "externo",
                "responsable": c,
                "viaje_uf": 0.0,
                "aloj_uf": 0.0,
                "alm_uf": 0.0,
                "inc_uf": 0.0,
                "sueldo_uf": 0.0,
                "flete_uf": flete_city,
                "pxq_total_uf": pxq_total,
                "material_uf": mat_city,
                "total_uf": pxq_total + flete_city + mat_city,
                "gps_total": gps_use,
                "horas_instal_total": safe_float(H.get(c, 0.0), 0.0),
            })

    df_city = pd.DataFrame(city_rows).sort_values("total_uf", ascending=False)
    df_tech = pd.DataFrame(tech_cost_rows).sort_values("total_uf", ascending=False)

    baseline = total_all_external()
    final_total = df_city["total_uf"].sum()

    comp = df_city[[
        "viaje_uf","aloj_uf","alm_uf","inc_uf","sueldo_uf","flete_uf","pxq_total_uf","material_uf","total_uf"
    ]].sum().to_dict()

    df_resumen = pd.DataFrame([{
        "baseline_all_external_uf": baseline,
        "final_total_uf": final_total,
        "savings_uf": baseline - final_total,
        "n_internal_cities": int((df_city["tipo_final"] == "interno").sum()),
        "n_external_cities": int((df_city["tipo_final"] == "externo").sum()),
        "santiago_gps_total": santiago_gps_total,
        "santiago_gps_internal": santiago_inst_gps,
        "santiago_gps_external": santiago_gps_ext,
        **{f"sum_{k}": v for k, v in comp.items()}
    }])

    df_demand = demanda.copy()
    df_demand["material_uf"] = df_demand["ciudad"].map(MATERIAL_UF)
    df_demand["pxq_uf_gps"] = df_demand["ciudad"].map(PXQ_UF_POR_GPS)
    df_demand["flete_uf"] = df_demand["ciudad"].map(FLETE_UF)

    df_params = pd.DataFrame([{"parametro": k, "valor": v} for k, v in param.items()])

    out_path = os.path.join(OUTPUTS_DIR, "resultado_optimizacion_gps_v6.xlsx")
    with pd.ExcelWriter(out_path) as w:
        df_resumen.to_excel(w, index=False, sheet_name="Resumen_Total")
        df_city.to_excel(w, index=False, sheet_name="Costos_por_Ciudad")
        df_tech.to_excel(w, index=False, sheet_name="Costos_por_Tecnico")
        df_plan.to_excel(w, index=False, sheet_name="Plan_Diario")
        df_demand.to_excel(w, index=False, sheet_name="Demanda_y_Materiales")
        df_params.to_excel(w, index=False, sheet_name="Parametros")

    print("[OK] ->", out_path)
    print("[OK] Total final (UF):", round(final_total, 4))
    print("[OK] Baseline all external (UF):", round(baseline, 4))
    print("[OK] Ahorro (UF):", round(baseline - final_total, 4))
    print("[OK] Santiago GPS total / internal / external:",
          round(santiago_gps_total, 2), round(santiago_inst_gps, 2), round(santiago_gps_ext, 2))

if __name__ == "__main__":
    run_all()
