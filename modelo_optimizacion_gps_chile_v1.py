# modelo_optimizacion_gps_chile_v2.py
# Optimización costos instalación GPS (Chile) – V2 (FIX: bases, capacidad real por técnico, flete no duplicado)
#
# Qué corrige (sin “forzar” internos, pero eliminando sesgos/bichos):
# 1) Capacidad REAL por técnico:
#    - días disponibles técnico = dias_semana_proyecto(tecnico) * SEMANAS
#    - NO usar DIAS_MAX global (eso infla/rompe la lógica y la coherencia Fase1/Fase2).
# 2) Bases NO se pueden “soltar” por metaheurística:
#    - si una ciudad es base de un técnico y tiene demanda, queda anclada al técnico.
#    - evita el caso absurdo: Calama/Chillán externos “aunque son base”.
# 3) Flete interno se cobra 1 vez por ciudad (si ese técnico instala algo en esa ciudad),
#    NO cada día (antes se duplicaba y hacía carísimo lo interno sin razón).
# 4) Guardrails estrictos para PXQ/Flete:
#    - si falta ciudad o no parsea, ERROR (no se “silencia a 0”).
# 5) Decisión endógena real:
#    - “interno” = lo que efectivamente se asigna factiblemente en días,
#    - “externo” = remanente.
#
# Inputs: deja tus 10 excels en ./data/ con estos nombres:
#   demanda_ciudades.xlsx
#   tecnicos_internos.xlsx
#   costos_externos.xlsx
#   flete_ciudad.xlsx
#   materiales.xlsx
#   parametros.xlsx
#   matriz_distancia_km.xlsx
#   matriz_peajes.xlsx
#   matriz_costo_avion.xlsx
#   matriz_tiempo_avion.xlsx
#
# Output: ./outputs/plan_global_operativo.xlsx
#
# Requiere: pandas, numpy, openpyxl, pyomo, pulp (CBC)

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
    """
    Soporta coma decimal ("100,5") y strings con espacios.
    """
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
    """
    Si falta ciudad o valores no parseables/<=0 (según allow_zero), ERROR.
    Esto evita el bug: PXQ queda 0 por mismatch => externos “gratis”.
    """
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
        raise ValueError(f"[ERROR] {name}: valores inválidos. Ejemplos: {bad[:20]}")


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
DIAS_MAX_GLOBAL = DIAS_SEM * SEMANAS  # solo referencia global (no capacidad real por técnico)

HH_MES = safe_float(param.get("hh_mes"), 180.0)

ALOJ_UF = safe_float(param.get("alojamiento_uf_noche"), 1.1)
ALMU_UF = safe_float(param.get("almuerzo_uf_dia"), 0.5)
INCENTIVO_UF = safe_float(param.get("incentivo_por_gps"), 1.12)

PRECIO_BENCINA_UF_KM = safe_float(param.get("precio_bencina_uf_km"), 0.0)

demanda["vehiculos_1gps"] = demanda["vehiculos_1gps"].fillna(0).astype(float)
demanda["vehiculos_2gps"] = demanda["vehiculos_2gps"].fillna(0).astype(float)
demanda["gps_total"] = demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]
demanda["gps_total"] = demanda["gps_total"].round().astype(int)

GPS_TOTAL = dict(zip(demanda["ciudad"], demanda["gps_total"]))
V1 = dict(zip(demanda["ciudad"], demanda["vehiculos_1gps"]))
V2 = dict(zip(demanda["ciudad"], demanda["vehiculos_2gps"]))

# Kits
kits["tipo_kit"] = kits["tipo_kit"].astype(str)
KIT1_UF = safe_float(kits.loc[kits["tipo_kit"] == "1_GPS", "costo"].values[0], 0.0)
KIT2_UF = safe_float(kits.loc[kits["tipo_kit"] == "2_GPS", "costo"].values[0], 0.0)

def costo_materiales_ciudad(ciudad: str) -> float:
    return KIT1_UF * safe_float(V1.get(ciudad, 0.0), 0.0) + KIT2_UF * safe_float(V2.get(ciudad, 0.0), 0.0)

# PXQ y flete (guardrails)
pxq["ciudad"] = pxq["ciudad"].apply(norm_city)
flete["ciudad"] = flete["ciudad"].apply(norm_city)

PXQ_UF_POR_GPS = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))     # UF/GPS
FLETE_UF = dict(zip(flete["ciudad"], flete["costo_flete"]))       # UF (por ciudad si aplica)

require_mapping_coverage(PXQ_UF_POR_GPS, CIUDADES, "PXQ_UF_POR_GPS", allow_zero=False)
require_mapping_coverage(FLETE_UF, CIUDADES, "FLETE_UF", allow_zero=True)


# =========================
# 5) FUNCIONES BASE
# =========================
def base_tecnico(tecnico: str) -> str:
    return internos.loc[internos["tecnico"] == tecnico, "ciudad_base"].values[0]

def dias_semana_proyecto(tecnico: str) -> float:
    # este campo viene en DÍAS/SEMANA (ya corregido)
    return safe_float(internos.loc[internos["tecnico"] == tecnico, "hh_semana_proyecto"].values[0], 0.0)

def dias_disponibles_proyecto(tecnico: str) -> int:
    # FIX V2: capacidad real por técnico
    d = dias_semana_proyecto(tecnico) * SEMANAS
    return int(math.floor(d + 1e-9))  # entero conservador

def horas_semana_proyecto(tecnico: str) -> float:
    return dias_semana_proyecto(tecnico) * H_DIA

def horas_diarias(tecnico: str) -> float:
    # horas promedio por día laboral del técnico
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

def flete_aplica(ciudad: str, base: str, modo_llegada: str) -> bool:
    if ciudad == SANTIAGO and base == SANTIAGO and modo_llegada == "terrestre":
        return False
    return True

def costo_sueldo_proyecto_uf(tecnico: str) -> float:
    sueldo_mes = safe_float(internos.loc[internos["tecnico"] == tecnico, "sueldo_uf"].values[0], 0.0)
    hh_proy = horas_semana_proyecto(tecnico) * SEMANAS
    return sueldo_mes * (hh_proy / max(1e-9, HH_MES))

def costo_externo_uf(ciudad: str, gps_externos: int, base_ref: str = SANTIAGO, modo_ref: str = "terrestre") -> dict:
    gps_externos = int(max(0, gps_externos))
    pxq_unit = safe_float(PXQ_UF_POR_GPS.get(ciudad, 0.0), 0.0)
    pxq_total = pxq_unit * gps_externos

    fle = 0.0
    if gps_externos > 0 and flete_aplica(ciudad, base_ref, modo_ref):
        fle = safe_float(FLETE_UF.get(ciudad, 0.0), 0.0)

    return {
        "pxq_uf": pxq_total,
        "flete_uf": fle,
        "total_externo_sin_materiales_uf": pxq_total + fle,
    }

# Bases con demanda (anclas)
BASES = {t: base_tecnico(t) for t in TECNICOS}
BASES_CON_DEMANDA = {t: b for t, b in BASES.items() if int(max(0, GPS_TOTAL.get(b, 0))) > 0}


# =========================
# 6) FASE 1 – MILP (asigna regiones a técnicos o externo)
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

        # FIX V2: sueldo por día usa días disponibles del técnico
        sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
        dias_disp = max(1, dias_disponibles_proyecto(tecnico))
        sueldo_dia = sueldo_proy / dias_disp
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

    m.x = pyo.Var(m.C, m.T, m.M, domain=pyo.Binary)
    m.y = pyo.Var(m.C, domain=pyo.Binary)

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
        # FIX V2: capacidad por técnico, no DIAS_MAX_GLOBAL
        cap_t = max(0, dias_disponibles_proyecto(t))
        return sum(dias_total_aprox(t, c, mo) * mm.x[c, t, mo] for c in mm.C for mo in mm.M) <= cap_t
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

    pd.DataFrame(
        rows,
        columns=["ciudad", "tecnico", "modo", "costo_aprox_fase1_uf", "dias_aprox_fase1"]
    ).to_excel(os.path.join(OUTPUTS_DIR, "resultado_optimizacion_gps_fase1.xlsx"), index=False)

    return {"tech_cities": tech_cities}


# =========================
# 7) FASE 2 – SIMULACIÓN + ASIGNACIÓN FACTIBLE POR DÍAS
# =========================
def simulate_tech_schedule(tecnico: str, cities_list: list[str], gps_asignados: dict[str, int]):
    base = base_tecnico(tecnico)
    hd = horas_diarias(tecnico)
    gpd = gps_por_dia(tecnico)
    dias_disp = max(0, dias_disponibles_proyecto(tecnico))

    if hd <= 1e-9 or gpd <= 0 or dias_disp <= 0:
        return [], {"total_uf": 1e18}, False

    day = 1
    sleep_city = base

    plan = []
    # FIX V2: flete interno se cobra 1 vez por ciudad donde instala algo
    flete_ciudades_cobradas = set()

    cost = {"travel_uf": 0.0, "aloj_uf": 0.0, "alm_uf": 0.0, "inc_uf": 0.0, "sueldo_uf": 0.0, "flete_uf": 0.0}

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1, dias_disp)

    pending = {c: int(max(0, gps_asignados.get(c, 0))) for c in cities_list}

    def can_install_today(time_left_h: float) -> int:
        return int(math.floor(time_left_h / max(1e-9, TIEMPO_INST_GPS_H)))

    for c in cities_list:
        if pending.get(c, 0) <= 0:
            continue
        if day > dias_disp:
            break

        modo_in = choose_mode(sleep_city, c)
        tv = t_viaje(sleep_city, c, modo_in)
        cv = costo_viaje_uf(sleep_city, c, modo_in)

        # costos del día (siempre que el día existe)
        cost["travel_uf"] += cv
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia

        # Opción A: si tv>hh_dia y cambia de ciudad => día solo viaje
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
            if day > dias_disp:
                break
            tv = 0.0
            modo_in = None

        time_left = max(0.0, hd - tv)
        gps_can = can_install_today(time_left)
        gps_inst = min(pending[c], gps_can)

        horas_instal = gps_inst * TIEMPO_INST_GPS_H
        pending[c] -= gps_inst
        cost["inc_uf"] += INCENTIVO_UF * gps_inst

        # flete interno: 1 vez por ciudad si realmente instala >0 en esa ciudad
        if gps_inst > 0 and (c not in flete_ciudades_cobradas) and flete_aplica(c, base, modo_in if modo_in else "terrestre"):
            cost["flete_uf"] += safe_float(FLETE_UF.get(c, 0.0), 0.0)
            flete_ciudades_cobradas.add(c)

        sleep_city = c
        if sleep_city != base:
            cost["aloj_uf"] += ALOJ_UF

        plan.append({
            "tecnico": tecnico, "dia": day, "ciudad_trabajo": c,
            "horas_instal": horas_instal, "gps_inst": int(gps_inst),
            "viaje_modo_manana": modo_in, "viaje_h_manana": tv,
            "duerme_en": sleep_city, "nota": ""
        })
        day += 1

        while pending[c] > 0 and day <= dias_disp:
            gps_inst = min(pending[c], gpd)
            horas_instal = gps_inst * TIEMPO_INST_GPS_H
            pending[c] -= gps_inst

            cost["alm_uf"] += ALMU_UF
            cost["sueldo_uf"] += sueldo_dia
            cost["inc_uf"] += INCENTIVO_UF * gps_inst
            if sleep_city != base:
                cost["aloj_uf"] += ALOJ_UF

            # flete ya cobrado por ciudad
            if gps_inst > 0 and (c not in flete_ciudades_cobradas) and flete_aplica(c, base, "terrestre"):
                cost["flete_uf"] += safe_float(FLETE_UF.get(c, 0.0), 0.0)
                flete_ciudades_cobradas.add(c)

            plan.append({
                "tecnico": tecnico, "dia": day, "ciudad_trabajo": c,
                "horas_instal": horas_instal, "gps_inst": int(gps_inst),
                "viaje_modo_manana": None, "viaje_h_manana": 0.0,
                "duerme_en": sleep_city, "nota": ""
            })
            day += 1

    feasible = (day - 1) <= dias_disp
    cost["total_uf"] = sum(v for k, v in cost.items() if k != "total_uf")
    return plan, cost, feasible


def allocate_gps_work_factible(tech_cities: dict[str, list[str]]):
    """
    Asignación factible por días (capacidad real por técnico):
    - Orden por técnico: base (si tiene demanda) + ciudades asignadas
    - Bases con demanda quedan ancladas (no dependen de tech_cities)
    - travel_day si tv>hh_dia al cambiar de ciudad
    - remanente => externo
    """
    rem_gps = {c: int(max(0, GPS_TOTAL.get(c, 0))) for c in CIUDADES}
    gps_asignados = {t: defaultdict(int) for t in TECNICOS}

    for t in TECNICOS:
        base = base_tecnico(t)
        gpd = gps_por_dia(t)
        hd = horas_diarias(t)
        dias_disp = max(0, dias_disponibles_proyecto(t))

        if gpd <= 0 or hd <= 1e-9 or dias_disp <= 0:
            continue

        days_left = dias_disp
        current_city = base

        ordered = []
        # base primero si hay demanda
        if rem_gps.get(base, 0) > 0:
            ordered.append(base)

        # luego ciudades asignadas por Fase1/metaheurística
        ordered += [c for c in tech_cities.get(t, []) if c != base]

        for c in ordered:
            if rem_gps.get(c, 0) <= 0:
                continue
            if days_left <= 0:
                break

            modo = choose_mode(current_city, c)
            tv = t_viaje(current_city, c, modo)

            travel_day = 1 if (current_city != c and tv > hd) else 0
            if days_left - travel_day <= 0:
                break

            max_install_days = days_left - travel_day
            max_gps = max_install_days * gpd

            take = min(rem_gps[c], max_gps)
            take = int(max(0, take))
            if take <= 0:
                break

            gps_asignados[t][c] += take
            rem_gps[c] -= take

            install_days_used = int(math.ceil(take / max(1, gpd)))

            days_left -= (travel_day + install_days_used)
            current_city = c

            if days_left <= 0:
                break

    return gps_asignados, rem_gps


def total_cost_solution(tech_cities):
    gps_asignados, rem_gps = allocate_gps_work_factible(tech_cities)

    total = 0.0

    # internos
    for t in TECNICOS:
        cities = [c for c, g in gps_asignados[t].items() if g > 0]
        if not cities:
            continue
        base = base_tecnico(t)
        if base in cities:
            cities = [base] + [c for c in cities if c != base]

        plan, cst, feas = simulate_tech_schedule(t, cities, gps_asignados[t])
        if not feas:
            return 1e18
        total += cst["total_uf"]

    # externos (remanente)
    for c in CIUDADES:
        gps_ext = int(max(0, rem_gps.get(c, 0)))
        ext = costo_externo_uf(c, gps_externos=gps_ext)
        total += ext["total_externo_sin_materiales_uf"]

    # materiales (siempre)
    total += sum(costo_materiales_ciudad(c) for c in CIUDADES)

    return total


def improve_solution(tech_cities, iters=400, seed=42):
    """
    Metaheurística coherente, con ANCLAS:
    - No permite mover/soltar la base del técnico si esa base tiene demanda.
    - Movimientos:
      (A) mover una ciudad de un técnico a otro
      (B) drop una ciudad (queda externa)
      (C) add una ciudad externa a un técnico
    """
    best_tc = deepcopy(tech_cities)
    best_cost = total_cost_solution(best_tc)

    rng = np.random.default_rng(seed)
    cities_no_scl = [c for c in CIUDADES if c != SANTIAGO]

    def all_assigned(tc):
        s = set()
        for tt in TECNICOS:
            for cc in tc.get(tt, []):
                s.add(cc)
        return s

    def is_anchored_city(tt, cc):
        # ancla = base del técnico con demanda
        return (tt in BASES_CON_DEMANDA) and (BASES_CON_DEMANDA[tt] == cc)

    for _ in range(iters):
        tc2 = deepcopy(best_tc)

        move = int(rng.integers(0, 3))  # 0 move, 1 drop, 2 add
        assigned = all_assigned(tc2)

        donors = []
        for t in TECNICOS:
            lst = tc2.get(t, [])
            # donor si tiene alguna ciudad movible
            movable = [c for c in lst if not is_anchored_city(t, c)]
            if movable:
                donors.append(t)

        if move == 0 and donors:
            t_from = str(rng.choice(donors))
            movable = [c for c in tc2[t_from] if not is_anchored_city(t_from, c)]
            c = str(rng.choice(movable))

            t_to = str(rng.choice([t for t in TECNICOS if t != t_from]))
            tc2[t_from].remove(c)
            if c not in tc2[t_to]:
                tc2[t_to].append(c)

        elif move == 1 and donors:
            t_from = str(rng.choice(donors))
            movable = [c for c in tc2[t_from] if not is_anchored_city(t_from, c)]
            c = str(rng.choice(movable))
            tc2[t_from].remove(c)  # queda externo

        else:
            unassigned = [c for c in cities_no_scl if c not in assigned]
            if unassigned:
                c = str(rng.choice(unassigned))
                t_to = str(rng.choice(TECNICOS))
                # no agregues duplicados
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
    print(f"[INFO] DIAS_SEM={DIAS_SEM} SEMANAS={SEMANAS} H_DIA={H_DIA} TIEMPO_INST={TIEMPO_INST_GPS_H}")
    print(f"[INFO] INCENTIVO_UF={INCENTIVO_UF} PRECIO_BENCINA_UF_KM={PRECIO_BENCINA_UF_KM}")

    print("\n=== DEBUG CAPACIDAD INTERNOS (V2) ===")
    for t in TECNICOS:
        print(
            f"- {t:20s} base={base_tecnico(t):12s} "
            f"dias_sem_proy={dias_semana_proyecto(t):5.2f} "
            f"dias_disp={dias_disponibles_proyecto(t):2d} "
            f"hdia={horas_diarias(t):5.2f} gps/dia={gps_por_dia(t):3d} "
            f"sueldo_proy_uf={costo_sueldo_proyecto_uf(t):8.2f}"
        )

    print("\n=== DEBUG PXQ (UF/GPS) EJEMPLOS ===")
    for c in CIUDADES[:10]:
        print(f"- {c:15s} pxq={safe_float(PXQ_UF_POR_GPS.get(c), 0.0):8.2f}  flete={safe_float(FLETE_UF.get(c), 0.0):8.2f}")

    ws = solve_phase1()
    tech_cities = ws["tech_cities"]

    # mejora coherente
    tech_cities2, best_cost = improve_solution(tech_cities, iters=400)

    gps_asignados, rem_gps = allocate_gps_work_factible(tech_cities2)

    plan_rows = []
    cost_rows = []
    city_rows = []
    asign_rows = []

    # internos
    for t in TECNICOS:
        cities = [c for c, g in gps_asignados[t].items() if g > 0]
        if not cities:
            continue
        base = base_tecnico(t)
        if base in cities:
            cities = [base] + [c for c in cities if c != base]

        # tabla auditora: asignación por técnico-ciudad
        for c in cities:
            asign_rows.append({"tecnico": t, "ciudad": c, "gps_internos": int(gps_asignados[t][c])})

        plan, cst, feas = simulate_tech_schedule(t, cities, gps_asignados[t])
        if not feas:
            raise RuntimeError(f"Solución final infeasible para técnico {t}")

        plan_rows.extend(plan)
        cost_rows.append({
            "responsable": t,
            "tipo": "INTERNO",
            "travel_uf": cst["travel_uf"],
            "aloj_uf": cst["aloj_uf"],
            "alm_uf": cst["alm_uf"],
            "inc_uf": cst["inc_uf"],
            "sueldo_uf": cst["sueldo_uf"],
            "flete_uf": cst["flete_uf"],
            "pxq_uf": 0.0,
            "materiales_uf": 0.0,
            "total_uf": cst["total_uf"],
        })

    # externos por ciudad (remanente)
    for c in CIUDADES:
        gps_ext = int(max(0, rem_gps.get(c, 0)))
        ext = costo_externo_uf(c, gps_externos=gps_ext)
        gps_tot = int(max(0, GPS_TOTAL.get(c, 0)))

        city_rows.append({
            "ciudad": c,
            "gps_total": gps_tot,
            "gps_internos": int(max(0, gps_tot - gps_ext)),
            "gps_externos": gps_ext,
            "pxq_unit_uf_gps": safe_float(PXQ_UF_POR_GPS.get(c), 0.0),
            "pxq_uf": ext["pxq_uf"],
            "flete_uf": ext["flete_uf"],
            "materiales_uf": costo_materiales_ciudad(c),
            "total_externo_sin_materiales_uf": ext["total_externo_sin_materiales_uf"],
            "total_ciudad_uf": ext["total_externo_sin_materiales_uf"] + costo_materiales_ciudad(c),
        })

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

    # materiales como línea auditora
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
        gps_float = df_plan["gps_inst"].astype(float)
        if not np.all(gps_float == np.floor(gps_float)):
            raise RuntimeError("gps_inst tiene decimales. Debe ser entero.")
        df_plan["gps_inst"] = df_plan["gps_inst"].astype(int)

    df_cost = pd.DataFrame(cost_rows).sort_values(["tipo", "total_uf"], ascending=[True, False])
    df_city = pd.DataFrame(city_rows).sort_values(["total_ciudad_uf"], ascending=False)
    df_asign = pd.DataFrame(asign_rows).sort_values(["tecnico", "ciudad"]) if asign_rows else pd.DataFrame(columns=["tecnico", "ciudad", "gps_internos"])

    total_uf = df_cost["total_uf"].sum()

    resumen = pd.DataFrame([
        ["total_uf", total_uf],
        ["total_interno_uf", df_cost.loc[df_cost["tipo"] == "INTERNO", "total_uf"].sum()],
        ["total_externo_sin_materiales_uf", df_cost.loc[df_cost["tipo"] == "EXTERNO", "total_uf"].sum()],
        ["materiales_total_uf", materiales_total],
        ["gps_total", sum(int(max(0, GPS_TOTAL.get(c, 0))) for c in CIUDADES)],
        ["dias_semana", DIAS_SEM],
        ["semanas_proyecto", SEMANAS],
        ["horas_jornada", H_DIA],
        ["tiempo_inst_gps_h", TIEMPO_INST_GPS_H],
        ["nota", "V2: capacidad real por técnico; bases con demanda ancladas; flete interno 1 vez por ciudad; interno=endógeno."]
    ], columns=["metric", "value"])

    out_path = os.path.join(OUTPUTS_DIR, "plan_global_operativo.xlsx")
    with pd.ExcelWriter(out_path) as w:
        resumen.to_excel(w, index=False, sheet_name="Resumen_Total")
        df_city.to_excel(w, index=False, sheet_name="Costos_por_Ciudad")
        df_asign.to_excel(w, index=False, sheet_name="Asignacion_Internos")
        df_plan.to_excel(w, index=False, sheet_name="Plan_Diario")
        df_cost.to_excel(w, index=False, sheet_name="Costos_Detalle")

    print("[OK] ->", out_path)
    print("[OK] Costo total (UF):", round(total_uf, 4))
    print("[OK] best_cost evaluator (UF):", round(best_cost, 4))

    # chequeo rápido: bases con demanda quedaron internas?
    print("\n=== CHECK BASES CON DEMANDA (V2) ===")
    for t, b in BASES_CON_DEMANDA.items():
        tot = int(max(0, GPS_TOTAL.get(b, 0)))
        interno_b = int(sum(df_asign.loc[(df_asign["tecnico"] == t) & (df_asign["ciudad"] == b), "gps_internos"])) if not df_asign.empty else 0
        print(f"- {t:15s} base={b:12s} gps_total_base={tot:4d} gps_interno_base={interno_b:4d}")


if __name__ == "__main__":
    run_all()
