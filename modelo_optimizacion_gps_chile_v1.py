# modelo_optimizacion_gps_chile_FINAL_FIXED_v2.py
# Optimización costos instalación GPS (Chile) – FIX CRÍTICO: CAPACIDAD INTERNOS + BASES + ALLOC COHERENTE
#
# Qué estaba fallando (y por eso te salía 0 internos aunque PXQ=100 UF/GPS):
# 1) hh_semana_proyecto en tus datos NO es "días/semana". Es FTE de semana (0.75 = 75% de la semana).
#    Tu código lo interpretaba como 0.75 días/semana => ~0.875 h/día => gps_por_dia=0 => internos incapaces => 100% externos.
# 2) Incentivo: en parametros.xlsx está 0.12 (no 1.12). El 1.12 te inflaba costos internos.
# 3) Flete: no debe aplicar cuando la ciudad == base del técnico (si estás en base, no “fleteas” a ti mismo).
# 4) Asignación Fase 2: el allocator por días usaba gpd “full día” y no respetaba el recorte del primer día cuando hay viaje (tv<hd).
#    Se rehace la asignación usando la MISMA lógica operativa (día a día) que el plan, así no hay incoherencias.
#
# Resultado esperado con tus archivos:
# - Ya no sale 0 internos por artefacto.
# - Bases (Calama, Chillán) pueden quedar internas si hay capacidad/costo, no se van “mágicamente” a externos.
#
# Requiere: pandas, numpy, openpyxl, pyomo, pulp (CBC)
# Inputs en ./data/
# Output: ./outputs/plan_global_operativo.xlsx

import os
import math
from copy import deepcopy
from datetime import time as dt_time
from collections import defaultdict

import numpy as np
import pandas as pd
import pyomo.environ as pyo
import pulp

print("[INFO] RUNNING FILE:", __file__)

# =========================
# 0) CONFIG
# =========================
PATH = "data/"
OUTPUTS_DIR = "outputs"
SANTIAGO = "Santiago"
os.makedirs(OUTPUTS_DIR, exist_ok=True)

CBC_EXE = pulp.apis.PULP_CBC_CMD().path  # ruta al CBC que usa PuLP

# =========================
# 1) UTILIDADES
# =========================
def time_to_hours(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return 0.0
    if isinstance(x, dt_time):
        return x.hour + x.minute / 60.0 + x.second / 3600.0
    if isinstance(x, str) and ":" in x:
        parts = x.strip().split(":")
        hh = float(parts[0]) if len(parts) >= 1 else 0.0
        mm = float(parts[1]) if len(parts) >= 2 else 0.0
        ss = float(parts[2]) if len(parts) >= 3 else 0.0
        return hh + mm / 60.0 + ss / 3600.0
    try:
        return float(x)
    except Exception:
        return 0.0

def safe_float(x, default=0.0):
    # soporta coma decimal "100,5"
    try:
        if x is None:
            return default
        if isinstance(x, float) and np.isnan(x):
            return default
        if isinstance(x, dt_time):
            return time_to_hours(x)
        if isinstance(x, str):
            s = x.strip().replace(" ", "")
            if "," in s and "." not in s:
                s = s.replace(",", ".")
            return float(s)
        return float(x)
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
        print(f"\n[ERROR MATRIZ] {name}")
        if missing_rows:
            print(" - FALTAN FILAS:", missing_rows)
        if missing_cols:
            print(" - FALTAN COLUMNAS:", missing_cols)
        raise ValueError(f"Matriz {name} no cubre todas las ciudades.")

def require_mapping_coverage(mapping: dict, cities: list[str], name: str, allow_zero=False):
    missing = [c for c in cities if c not in mapping]
    if missing:
        raise ValueError(f"[ERROR] {name}: faltan ciudades: {missing}")

    bad = []
    for c in cities:
        v = mapping.get(c, None)
        vv = safe_float(v, None)
        if vv is None:
            bad.append((c, v))
        else:
            if (not allow_zero) and (vv <= 0):
                bad.append((c, v))
    if bad:
        raise ValueError(f"[ERROR] {name}: valores no válidos (<=0 o no parseables). Ejemplos: {bad[:20]}")

# =========================
# 2) CARGA DE DATOS (UF)
# =========================
demanda = pd.read_excel(os.path.join(PATH, "demanda_ciudades.xlsx"))
internos = pd.read_excel(os.path.join(PATH, "tecnicos_internos.xlsx"))
pxq = pd.read_excel(os.path.join(PATH, "costos_externos.xlsx"))
flete = pd.read_excel(os.path.join(PATH, "flete_ciudad.xlsx"))
kits = pd.read_excel(os.path.join(PATH, "materiales.xlsx"))
param_df = pd.read_excel(os.path.join(PATH, "parametros.xlsx"))

km = pd.read_excel(os.path.join(PATH, "matriz_distancia_km.xlsx"), index_col=0)
peajes = pd.read_excel(os.path.join(PATH, "matriz_peajes.xlsx"), index_col=0)           # UF
avion_cost = pd.read_excel(os.path.join(PATH, "matriz_costo_avion.xlsx"), index_col=0) # UF
avion_time = pd.read_excel(os.path.join(PATH, "matriz_tiempo_avion.xlsx"), index_col=0)

# =========================
# 3) NORMALIZACIÓN + SETS
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

internos["tecnico"] = internos["tecnico"].apply(norm_city)
internos["ciudad_base"] = internos["ciudad_base"].apply(norm_city)

TECNICOS = internos["tecnico"].tolist()
MODOS = ["terrestre", "avion"]

# =========================
# 4) PARÁMETROS / DEMANDA
# =========================
param = param_df.set_index("parametro")["valor"].to_dict()

H_DIA = safe_float(param.get("horas_jornada"), 7.0)
VEL = safe_float(param.get("velocidad_terrestre"), 80.0)
TIEMPO_INST_GPS_H = safe_float(param.get("tiempo_instalacion_gps"), 1.25)

DIAS_SEM = int(safe_float(param.get("dias_semana"), 6))
SEMANAS = int(safe_float(param.get("semanas_proyecto"), 4))
DIAS_MAX = DIAS_SEM * SEMANAS

HH_MES = safe_float(param.get("hh_mes"), 180.0)

ALOJ_UF = safe_float(param.get("alojamiento_uf_noche"), 1.1)
ALMU_UF = safe_float(param.get("almuerzo_uf_dia"), 0.5)

# FIX: incentivo real desde archivo (en tus datos es 0.12)
INCENTIVO_UF = safe_float(param.get("incentivo_por_gps"), 0.12)

# FIX: tu parametros.xlsx trae "precio_bencina" (no "precio_bencina_uf_km")
PRECIO_BENCINA_UF_KM = safe_float(param.get("precio_bencina_uf_km"), None)
if PRECIO_BENCINA_UF_KM is None:
    PRECIO_BENCINA_UF_KM = safe_float(param.get("precio_bencina"), 0.0)

demanda["vehiculos_1gps"] = demanda["vehiculos_1gps"].fillna(0).astype(float)
demanda["vehiculos_2gps"] = demanda["vehiculos_2gps"].fillna(0).astype(float)
demanda["gps_total"] = (demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]).round().astype(int)

GPS_TOTAL = dict(zip(demanda["ciudad"], demanda["gps_total"]))
V1 = dict(zip(demanda["ciudad"], demanda["vehiculos_1gps"]))
V2 = dict(zip(demanda["ciudad"], demanda["vehiculos_2gps"]))

# Kits
kits["tipo_kit"] = kits["tipo_kit"].astype(str)
KIT1_UF = safe_float(kits.loc[kits["tipo_kit"] == "1_GPS", "costo"].values[0], 0.0)
KIT2_UF = safe_float(kits.loc[kits["tipo_kit"] == "2_GPS", "costo"].values[0], 0.0)

def costo_materiales_ciudad(ciudad: str) -> float:
    return KIT1_UF * safe_float(V1.get(ciudad, 0.0), 0.0) + KIT2_UF * safe_float(V2.get(ciudad, 0.0), 0.0)

# PXQ y flete
pxq["ciudad"] = pxq["ciudad"].apply(norm_city)
flete["ciudad"] = flete["ciudad"].apply(norm_city)

PXQ_UF_POR_GPS = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))   # UF/GPS
FLETE_UF = dict(zip(flete["ciudad"], flete["costo_flete"]))     # UF por ciudad (si aplica)

require_mapping_coverage(PXQ_UF_POR_GPS, CIUDADES, "PXQ_UF_POR_GPS", allow_zero=False)
require_mapping_coverage(FLETE_UF, CIUDADES, "FLETE_UF", allow_zero=True)

# =========================
# 5) FUNCIONES BASE
# =========================
def base_tecnico(tecnico: str) -> str:
    return internos.loc[internos["tecnico"] == tecnico, "ciudad_base"].values[0]

def dias_semana_proyecto(tecnico: str) -> float:
    """
    FIX CRÍTICO:
    hh_semana_proyecto en tu archivo viene como FTE (0.75 = 75% de la semana), no "días/semana".
    Heurística robusta:
    - si 0 <= v <= 1.5  => interpretarlo como fracción de semana => dias = v * DIAS_SEM
    - si 1.5 < v <= DIAS_SEM+0.5 => interpretarlo como días/semana
    - si v > DIAS_SEM+0.5 => interpretarlo como horas/semana => dias = v / H_DIA
    """
    v = safe_float(internos.loc[internos["tecnico"] == tecnico, "hh_semana_proyecto"].values[0], 0.0)

    if v <= 0:
        return 0.0
    if 0.0 < v <= 1.5:
        return v * DIAS_SEM
    if 1.5 < v <= (DIAS_SEM + 0.5):
        return v
    # fallback: horas/semana
    return v / max(1e-9, H_DIA)

def horas_semana_proyecto(tecnico: str) -> float:
    return dias_semana_proyecto(tecnico) * H_DIA

def horas_diarias(tecnico: str) -> float:
    return horas_semana_proyecto(tecnico) / max(1e-9, DIAS_SEM)

def gps_por_dia(tecnico: str) -> int:
    hd = horas_diarias(tecnico)
    return int(math.floor(hd / max(1e-9, TIEMPO_INST_GPS_H)))

def t_viaje(ciudad_origen: str, ciudad_destino: str, modo: str) -> float:
    if ciudad_origen == ciudad_destino:
        return 0.0
    if modo == "terrestre":
        return safe_float(km.loc[ciudad_origen, ciudad_destino], 0.0) / max(1e-9, VEL)
    return time_to_hours(avion_time.loc[ciudad_origen, ciudad_destino])

def costo_viaje_uf(ciudad_origen: str, ciudad_destino: str, modo: str) -> float:
    if ciudad_origen == ciudad_destino:
        return 0.0
    if modo == "terrestre":
        dist_km = safe_float(km.loc[ciudad_origen, ciudad_destino], 0.0)
        peaje_uf = safe_float(peajes.loc[ciudad_origen, ciudad_destino], 0.0)
        return peaje_uf + PRECIO_BENCINA_UF_KM * dist_km
    return safe_float(avion_cost.loc[ciudad_origen, ciudad_destino], 0.0)

def choose_mode(o, d):
    if o == d:
        return "terrestre"
    road = costo_viaje_uf(o, d, "terrestre")
    air = costo_viaje_uf(o, d, "avion")
    return "avion" if air < road else "terrestre"

def flete_aplica(ciudad: str, base_ref: str, modo_llegada: str) -> bool:
    """
    FIX: no aplicar flete cuando ciudad == base (no tiene sentido fletearte a ti mismo).
    Mantiene excepción Santiago->Santiago terrestre (tampoco flete).
    """
    if ciudad == base_ref:
        return False
    if ciudad == SANTIAGO and base_ref == SANTIAGO and modo_llegada == "terrestre":
        return False
    return True

def costo_sueldo_proyecto_uf(tecnico: str) -> float:
    sueldo_mes = safe_float(internos.loc[internos["tecnico"] == tecnico, "sueldo_uf"].values[0], 0.0)
    hh_proy = horas_semana_proyecto(tecnico) * SEMANAS
    return sueldo_mes * (hh_proy / max(1e-9, HH_MES))

def costo_externo_uf(ciudad: str, gps_externos: int, base_ref: str = SANTIAGO) -> dict:
    gps_externos = int(max(0, gps_externos))
    pxq_unit = safe_float(PXQ_UF_POR_GPS.get(ciudad, 0.0), 0.0)
    pxq_total = pxq_unit * gps_externos

    fle = 0.0
    # para externos, referencia es “Santiago” (envío / activación desde central)
    if gps_externos > 0 and flete_aplica(ciudad, base_ref, "terrestre"):
        fle = safe_float(FLETE_UF.get(ciudad, 0.0), 0.0)

    return {"pxq_uf": pxq_total, "flete_uf": fle, "total_externo_sin_materiales_uf": pxq_total + fle}

# =========================
# 6) FASE 1 – MILP (seed inicial tech_cities)
# =========================
def solve_phase1():
    C_REG = [c for c in CIUDADES if c != SANTIAGO]

    if not CBC_EXE or not os.path.exists(CBC_EXE):
        raise RuntimeError("No se encontró CBC vía PuLP. Reinstala pulp o revisa PULP_CBC_CMD().path")

    def dias_total_aprox(tecnico: str, ciudad: str, modo: str) -> int:
        base = base_tecnico(tecnico)
        hd = horas_diarias(tecnico)
        gpd = gps_por_dia(tecnico)
        if hd <= 1e-9 or gpd <= 0:
            return 10**9

        tv = t_viaje(base, ciudad, modo)
        travel_day = 1 if (ciudad != base and tv > hd) else 0

        gps = int(max(0, GPS_TOTAL.get(ciudad, 0)))
        install_days = int(math.ceil(gps / max(1, gpd))) if gps > 0 else 0
        return travel_day + install_days

    def costo_interno_aprox_uf(tecnico: str, ciudad: str, modo: str) -> float:
        base = base_tecnico(tecnico)
        dias = dias_total_aprox(tecnico, ciudad, modo)
        if dias >= 10**8:
            return 1e15

        viaje = costo_viaje_uf(base, ciudad, modo)

        sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
        sueldo_dia = sueldo_proy / max(1, DIAS_MAX)
        sue = sueldo_dia * dias

        alm = ALMU_UF * dias
        alo = ALOJ_UF * dias if ciudad != base else 0.0
        inc = INCENTIVO_UF * int(max(0, GPS_TOTAL.get(ciudad, 0)))

        fle = safe_float(FLETE_UF.get(ciudad, 0.0), 0.0) if flete_aplica(ciudad, base, modo) else 0.0

        return viaje + sue + alm + alo + inc + fle

    m = pyo.ConcreteModel()
    m.C = pyo.Set(initialize=C_REG)
    m.T = pyo.Set(initialize=TECNICOS)
    m.M = pyo.Set(initialize=MODOS)

    m.x = pyo.Var(m.C, m.T, m.M, domain=pyo.Binary)  # ciudad c asignada a tecnico t por modo m
    m.y = pyo.Var(m.C, domain=pyo.Binary)            # 1 si ciudad se hace interna, 0 si externo

    def obj_rule(mm):
        cost = 0.0
        for c in mm.C:
            cost += sum(mm.x[c, t, mo] * costo_interno_aprox_uf(t, c, mo) for t in mm.T for mo in mm.M)
            ext = costo_externo_uf(c, gps_externos=int(max(0, GPS_TOTAL.get(c, 0))))
            cost += (1 - mm.y[c]) * ext["total_externo_sin_materiales_uf"]
        return cost

    m.OBJ = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

    def link_xy(mm, c, t, mo):
        return mm.x[c, t, mo] <= mm.y[c]
    m.LINK = pyo.Constraint(m.C, m.T, m.M, rule=link_xy)

    def unica(mm, c):
        return sum(mm.x[c, t, mo] for t in mm.T for mo in mm.M) == mm.y[c]
    m.UNICA = pyo.Constraint(m.C, rule=unica)

    def cap(mm, t):
        return sum(dias_total_aprox(t, c, mo) * mm.x[c, t, mo] for c in mm.C for mo in mm.M) <= DIAS_MAX
    m.CAP = pyo.Constraint(m.T, rule=cap)

    solver = pyo.SolverFactory("cbc", executable=CBC_EXE)
    solver.solve(m, tee=False)

    tech_cities = {t: [] for t in TECNICOS}
    rows = []
    for c in C_REG:
        for t in TECNICOS:
            for mo in MODOS:
                if pyo.value(m.x[c, t, mo]) > 0.5:
                    tech_cities[t].append(c)
                    rows.append([c, t, mo, costo_interno_aprox_uf(t, c, mo), dias_total_aprox(t, c, mo)])

    pd.DataFrame(rows, columns=["ciudad", "tecnico", "modo", "costo_aprox_fase1_uf", "dias_aprox_fase1"]).to_excel(
        os.path.join(OUTPUTS_DIR, "resultado_optimizacion_gps_fase1.xlsx"), index=False
    )

    return {"tech_cities": tech_cities}

# =========================
# 7) FASE 2 – ASIGNACIÓN + PLAN (MISMA LÓGICA OPERATIVA)
# =========================
def build_plan_and_allocate_for_tech(tecnico: str, ordered_cities: list[str], rem_gps: dict[str, int]):
    """
    Simula día a día como operación real:
    - Si tv > hh_dia y cambio de ciudad => día solo viaje (Opción A)
    - Si tv <= hh_dia => instala lo que quepa ese día (recortado por viaje)
    - Continúa instalando en la misma ciudad días siguientes (full hdía)
    - Flete: 1 vez por ciudad si aplica (y NO aplica si ciudad == base)
    Devuelve:
      plan_rows, cost_dict, installed_by_city (para este técnico)
    """
    base = base_tecnico(tecnico)
    hd = horas_diarias(tecnico)
    if hd <= 1e-9:
        return [], {"total_uf": 0.0}, {}

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1, DIAS_MAX)

    day = 1
    sleep_city = base

    plan = []
    installed = defaultdict(int)

    cost = {"travel_uf": 0.0, "aloj_uf": 0.0, "alm_uf": 0.0, "inc_uf": 0.0, "sueldo_uf": 0.0, "flete_uf": 0.0}

    def can_install(time_left_h: float) -> int:
        return int(math.floor(time_left_h / max(1e-9, TIEMPO_INST_GPS_H)))

    for c in ordered_cities:
        if day > DIAS_MAX:
            break

        pending = int(max(0, rem_gps.get(c, 0)))
        if pending <= 0:
            continue

        modo_in = choose_mode(sleep_city, c)
        tv = t_viaje(sleep_city, c, modo_in)
        cv = costo_viaje_uf(sleep_city, c, modo_in)

        # costos diarios base (siempre que "ocupas" el día)
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia
        cost["travel_uf"] += cv

        # flete 1 vez por ciudad si aplica
        if flete_aplica(c, base, modo_in):
            cost["flete_uf"] += safe_float(FLETE_UF.get(c, 0.0), 0.0)

        # Opción A: día solo viaje (si no alcanza a trabajar)
        if tv > hd and sleep_city != c:
            sleep_city = c
            if sleep_city != base:
                cost["aloj_uf"] += ALOJ_UF

            plan.append({
                "tecnico": tecnico, "dia": day, "ciudad_trabajo": c,
                "horas_instal": 0.0, "gps_inst": 0,
                "viaje_modo_manana": modo_in, "viaje_h_manana": tv,
                "duerme_en": sleep_city, "nota": "Día solo viaje (tv>hh_dia)"
            })
            day += 1
            if day > DIAS_MAX:
                break

            # siguiente día en la ciudad (sin viaje)
            tv = 0.0
            modo_in = None

            # nuevo día: almuerzo + sueldo
            cost["alm_uf"] += ALMU_UF
            cost["sueldo_uf"] += sueldo_dia

        # día con posible instalación (primer día en ciudad)
        time_left = max(0.0, hd - tv)
        gps_can = can_install(time_left)
        gps_inst = min(pending, gps_can)

        hours_instal = gps_inst * TIEMPO_INST_GPS_H
        pending -= gps_inst

        installed[c] += gps_inst
        rem_gps[c] -= gps_inst
        cost["inc_uf"] += INCENTIVO_UF * gps_inst

        sleep_city = c
        if sleep_city != base:
            cost["aloj_uf"] += ALOJ_UF

        plan.append({
            "tecnico": tecnico, "dia": day, "ciudad_trabajo": c,
            "horas_instal": float(hours_instal), "gps_inst": int(gps_inst),
            "viaje_modo_manana": modo_in, "viaje_h_manana": float(tv),
            "duerme_en": sleep_city, "nota": ""
        })
        day += 1

        # días completos en la misma ciudad
        while pending > 0 and day <= DIAS_MAX:
            gps_can_full = can_install(hd)
            gps_inst2 = min(pending, gps_can_full)
            hours_instal2 = gps_inst2 * TIEMPO_INST_GPS_H

            pending -= gps_inst2

            installed[c] += gps_inst2
            rem_gps[c] -= gps_inst2
            cost["inc_uf"] += INCENTIVO_UF * gps_inst2

            cost["alm_uf"] += ALMU_UF
            cost["sueldo_uf"] += sueldo_dia
            if sleep_city != base:
                cost["aloj_uf"] += ALOJ_UF

            plan.append({
                "tecnico": tecnico, "dia": day, "ciudad_trabajo": c,
                "horas_instal": float(hours_instal2), "gps_inst": int(gps_inst2),
                "viaje_modo_manana": None, "viaje_h_manana": 0.0,
                "duerme_en": sleep_city, "nota": ""
            })
            day += 1

    cost["total_uf"] = sum(cost.values())
    return plan, cost, dict(installed)

def total_cost_solution(tech_cities):
    rem = {c: int(max(0, GPS_TOTAL.get(c, 0))) for c in CIUDADES}
    total_internal = 0.0

    for t in TECNICOS:
        base = base_tecnico(t)
        ordered = []
        if rem.get(base, 0) > 0:
            ordered.append(base)
        ordered += [c for c in tech_cities.get(t, []) if c != base]

        plan, cst, installed = build_plan_and_allocate_for_tech(t, ordered, rem)
        if sum(installed.values()) > 0:
            total_internal += cst["total_uf"]

    total_external = 0.0
    for c in CIUDADES:
        gps_ext = int(max(0, rem.get(c, 0)))
        total_external += costo_externo_uf(c, gps_ext)["total_externo_sin_materiales_uf"]

    total_materiales = sum(costo_materiales_ciudad(c) for c in CIUDADES)
    return total_internal + total_external + total_materiales

def improve_solution(tech_cities, iters=500, seed=42):
    best_tc = deepcopy(tech_cities)
    best_cost = total_cost_solution(best_tc)

    rng = np.random.default_rng(seed)
    cities_no_scl = [c for c in CIUDADES if c != SANTIAGO]

    def all_assigned(tc):
        s = set()
        for t in TECNICOS:
            for c in tc.get(t, []):
                s.add(c)
        return s

    for _ in range(iters):
        tc2 = deepcopy(best_tc)

        move = int(rng.integers(0, 3))  # 0 move, 1 drop, 2 add
        assigned = all_assigned(tc2)
        donors = [t for t in TECNICOS if len(tc2.get(t, [])) > 0]

        if move == 0 and donors:
            t_from = str(rng.choice(donors))
            c = str(rng.choice(tc2[t_from]))
            t_to = str(rng.choice([t for t in TECNICOS if t != t_from]))
            tc2[t_from].remove(c)
            if c not in tc2[t_to]:
                tc2[t_to].append(c)

        elif move == 1 and donors:
            t_from = str(rng.choice(donors))
            c = str(rng.choice(tc2[t_from]))
            tc2[t_from].remove(c)  # queda externo

        else:
            unassigned = [c for c in cities_no_scl if c not in assigned]
            if unassigned:
                c = str(rng.choice(unassigned))
                t_to = str(rng.choice(TECNICOS))
                if c not in tc2[t_to]:
                    tc2[t_to].append(c)

        new_cost = total_cost_solution(tc2)
        if new_cost + 1e-6 < best_cost:
            best_cost = new_cost
            best_tc = tc2

    return best_tc, best_cost

# =========================
# 8) RUN + EXPORT
# =========================
def run_all():
    print(f"[INFO] CBC_EXE = {CBC_EXE}")
    print(f"[INFO] DIAS_MAX={DIAS_MAX} DIAS_SEM={DIAS_SEM} SEMANAS={SEMANAS} H_DIA={H_DIA} TIEMPO_INST={TIEMPO_INST_GPS_H}")
    print(f"[INFO] INCENTIVO_UF={INCENTIVO_UF} PRECIO_BENCINA_UF_KM={PRECIO_BENCINA_UF_KM}")

    print("\n=== DEBUG CAPACIDAD INTERNOS (POST-FIX) ===")
    for t in TECNICOS:
        print(
            f"- {t:20s} base={base_tecnico(t):12s} "
            f"fte_raw={safe_float(internos.loc[internos['tecnico']==t,'hh_semana_proyecto'].values[0],0.0):5.2f} "
            f"dias_sem_proy={dias_semana_proyecto(t):5.2f} "
            f"hdia={horas_diarias(t):5.2f} gps/dia={gps_por_dia(t):3d} "
            f"sueldo_proy_uf={costo_sueldo_proyecto_uf(t):8.2f}"
        )

    ws = solve_phase1()
    tech_cities = ws["tech_cities"]

    # mejora sobre lo que realmente ejecutas
    tech_cities2, best_cost = improve_solution(tech_cities, iters=500)

    # construir plan final + costos con asignación real
    rem = {c: int(max(0, GPS_TOTAL.get(c, 0))) for c in CIUDADES}

    plan_rows = []
    cost_rows = []
    city_installed_internal = defaultdict(int)

    # internos
    for t in TECNICOS:
        base = base_tecnico(t)
        ordered = []
        if rem.get(base, 0) > 0:
            ordered.append(base)
        ordered += [c for c in tech_cities2.get(t, []) if c != base]

        plan, cst, installed = build_plan_and_allocate_for_tech(t, ordered, rem)
        if sum(installed.values()) <= 0:
            continue

        for c, g in installed.items():
            city_installed_internal[c] += int(g)

        plan_rows.extend(plan)
        cost_rows.append({
            "responsable": t,
            "tipo": "INTERNO",
            "travel_uf": cst.get("travel_uf", 0.0),
            "aloj_uf": cst.get("aloj_uf", 0.0),
            "alm_uf": cst.get("alm_uf", 0.0),
            "inc_uf": cst.get("inc_uf", 0.0),
            "sueldo_uf": cst.get("sueldo_uf", 0.0),
            "flete_uf": cst.get("flete_uf", 0.0),
            "pxq_uf": 0.0,
            "materiales_uf": 0.0,
            "total_uf": cst.get("total_uf", 0.0),
        })

    # externos por ciudad (remanente final)
    city_rows = []
    for c in CIUDADES:
        gps_total = int(max(0, GPS_TOTAL.get(c, 0)))
        gps_int = int(max(0, city_installed_internal.get(c, 0)))
        gps_ext = int(max(0, rem.get(c, 0)))

        ext = costo_externo_uf(c, gps_ext)

        city_rows.append({
            "ciudad": c,
            "gps_total": gps_total,
            "gps_internos": gps_int,
            "gps_externos": gps_ext,
            "pxq_unit_uf_gps": safe_float(PXQ_UF_POR_GPS.get(c), 0.0),
            "pxq_uf": ext["pxq_uf"],
            "flete_uf": ext["flete_uf"],
            "materiales_uf": costo_materiales_ciudad(c),
            "total_externo_sin_materiales_uf": ext["total_externo_sin_materiales_uf"],
            "total_ciudad_uf": ext["total_externo_sin_materiales_uf"] + costo_materiales_ciudad(c),
        })

        if gps_ext > 0:
            cost_rows.append({
                "responsable": c,
                "tipo": "EXTERNO",
                "travel_uf": 0.0,
                "aloj_uf": 0.0,
                "alm_uf": 0.0,
                "inc_uf": 0.0,
                "sueldo_uf": 0.0,
                "flete_uf": ext["flete_uf"],
                "pxq_uf": ext["pxq_uf"],
                "materiales_uf": 0.0,
                "total_uf": ext["total_externo_sin_materiales_uf"],
            })

    materiales_total = sum(costo_materiales_ciudad(c) for c in CIUDADES)
    cost_rows.append({
        "responsable": "MATERIALES (TOTAL)",
        "tipo": "MATERIALES",
        "travel_uf": 0.0,
        "aloj_uf": 0.0,
        "alm_uf": 0.0,
        "inc_uf": 0.0,
        "sueldo_uf": 0.0,
        "flete_uf": 0.0,
        "pxq_uf": 0.0,
        "materiales_uf": materiales_total,
        "total_uf": materiales_total,
    })

    df_plan = pd.DataFrame(plan_rows)
    if df_plan.empty:
        df_plan = pd.DataFrame(columns=[
            "tecnico", "dia", "ciudad_trabajo", "horas_instal", "gps_inst",
            "viaje_modo_manana", "viaje_h_manana", "duerme_en", "nota"
        ])
    else:
        df_plan = df_plan.sort_values(["tecnico", "dia"]).reset_index(drop=True)
        df_plan["gps_inst"] = df_plan["gps_inst"].astype(int)

    df_cost = pd.DataFrame(cost_rows)
    if not df_cost.empty:
        df_cost = df_cost.sort_values(["tipo", "total_uf"], ascending=[True, False])

    df_city = pd.DataFrame(city_rows).sort_values(["total_ciudad_uf"], ascending=False)

    total_uf = float(df_cost["total_uf"].sum()) if not df_cost.empty else 0.0

    resumen = pd.DataFrame([
        ["total_uf", total_uf],
        ["total_interno_uf", float(df_cost.loc[df_cost["tipo"] == "INTERNO", "total_uf"].sum()) if not df_cost.empty else 0.0],
        ["total_externo_sin_materiales_uf", float(df_cost.loc[df_cost["tipo"] == "EXTERNO", "total_uf"].sum()) if not df_cost.empty else 0.0],
        ["materiales_total_uf", materiales_total],
        ["gps_total", sum(int(max(0, GPS_TOTAL.get(c, 0))) for c in CIUDADES)],
        ["gps_internos_total", int(sum(city_installed_internal.values()))],
        ["gps_externos_total", int(sum(max(0, rem.get(c, 0)) for c in CIUDADES))],
        ["dias_max_proyecto", DIAS_MAX],
        ["dias_semana", DIAS_SEM],
        ["horas_jornada", H_DIA],
        ["tiempo_inst_gps_h", TIEMPO_INST_GPS_H],
        ["nota", "FIX: hh_semana_proyecto interpretado como FTE (0.75=>4.5 días/sem). Incentivo corregido. Flete no aplica en base. Asignación F2 coherente día-a-día."]
    ], columns=["metric", "value"])

    out_path = os.path.join(OUTPUTS_DIR, "plan_global_operativo.xlsx")
    with pd.ExcelWriter(out_path) as w:
        resumen.to_excel(w, index=False, sheet_name="Resumen_Total")
        df_city.to_excel(w, index=False, sheet_name="Costos_por_Ciudad")
        df_plan.to_excel(w, index=False, sheet_name="Plan_Diario")
        df_cost.to_excel(w, index=False, sheet_name="Costos_Detalle")

    print("[OK] ->", out_path)
    print("[OK] Costo total (UF):", round(total_uf, 4))
    print("[OK] (debug) best_cost evaluator (UF):", round(best_cost, 4))

if __name__ == "__main__":
    run_all()
