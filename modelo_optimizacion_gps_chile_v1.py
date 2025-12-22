# modelo_optimizacion_gps_chile_FINAL_AUDIT_MAX.py
# Optimización costos instalación GPS (Chile) – MAX DESGLOSE / AUDITORÍA
#
# Objetivo:
# - Mantener tu lógica actual (Fase 1 MILP + Fase 2 asignación factible por días + Opción A)
# - NO “forzar” internos.
# - Pero entregar el EXCEL con el máximo desglose posible para analizar TODOS los costos:
#   * Resumen ejecutivo (UF y %)
#   * Costos por ciudad ultra-desglosados (PXQ, flete, materiales, UF/GPS, shares)
#   * Pareto / ranking por drivers (PXQ, materiales, flete)
#   * Comparativo interno vs externo por ciudad (aprox Fase 1: breakeven y delta)
#   * Detalle de asignación interna (GPS asignados por técnico x ciudad, días usados, días viaje, días instalación)
#   * Costos internos por técnico (travel/aloj/alm/sueldo/inc/flete) + UF/GPS interno
#   * Plan diario (si hay internos) + trazabilidad de viajes
#   * Parámetros usados + capacidad real de cada técnico (hdía, gps/día, días disponibles)
#   * Auditoría de inputs: PXQ unit, flete, kits, demanda
#
# Requiere: pandas, numpy, openpyxl, pyomo, pulp (CBC)
# Inputs en ./data/
# Output: ./outputs/plan_global_operativo_MAX_DESGLOSE.xlsx

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
    # soporta coma decimal
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

def pct(a, b):
    return 0.0 if abs(b) < 1e-12 else (a / b)

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
peajes = pd.read_excel(os.path.join(PATH, "matriz_peajes.xlsx"), index_col=0)            # UF
avion_cost = pd.read_excel(os.path.join(PATH, "matriz_costo_avion.xlsx"), index_col=0)  # UF
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
INCENTIVO_UF = safe_float(param.get("incentivo_por_gps"), 0.12)

PRECIO_BENCINA_UF_KM = safe_float(param.get("precio_bencina_uf_km"), 0.0)

demanda["vehiculos_1gps"] = demanda["vehiculos_1gps"].fillna(0).astype(float)
demanda["vehiculos_2gps"] = demanda["vehiculos_2gps"].fillna(0).astype(float)
demanda["gps_total"] = (demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]).round().astype(int)

GPS_TOTAL = dict(zip(demanda["ciudad"], demanda["gps_total"]))
V1 = dict(zip(demanda["ciudad"], demanda["vehiculos_1gps"]))
V2 = dict(zip(demanda["ciudad"], demanda["vehiculos_2gps"]))

kits["tipo_kit"] = kits["tipo_kit"].astype(str)
KIT1_UF = safe_float(kits.loc[kits["tipo_kit"] == "1_GPS", "costo"].values[0], 0.0)
KIT2_UF = safe_float(kits.loc[kits["tipo_kit"] == "2_GPS", "costo"].values[0], 0.0)

def costo_materiales_ciudad(ciudad: str) -> float:
    return KIT1_UF * safe_float(V1.get(ciudad, 0.0), 0.0) + KIT2_UF * safe_float(V2.get(ciudad, 0.0), 0.0)

# PXQ y flete
pxq["ciudad"] = pxq["ciudad"].apply(norm_city)
flete["ciudad"] = flete["ciudad"].apply(norm_city)

PXQ_UF_POR_GPS = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))      # UF/GPS
FLETE_UF = dict(zip(flete["ciudad"], flete["costo_flete"]))        # UF ciudad si aplica

require_mapping_coverage(PXQ_UF_POR_GPS, CIUDADES, "PXQ_UF_POR_GPS", allow_zero=False)
require_mapping_coverage(FLETE_UF, CIUDADES, "FLETE_UF", allow_zero=True)

# =========================
# 5) FUNCIONES BASE
# =========================
def base_tecnico(tecnico: str) -> str:
    return internos.loc[internos["tecnico"] == tecnico, "ciudad_base"].values[0]

def dias_semana_proyecto(tecnico: str) -> float:
    # tu input declarado: viene en DÍAS/SEMANA
    return safe_float(internos.loc[internos["tecnico"] == tecnico, "hh_semana_proyecto"].values[0], 0.0)

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

def flete_aplica(ciudad: str, base: str, modo_llegada: str) -> bool:
    # regla existente
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
        "pxq_unit_uf_gps": pxq_unit,
        "pxq_uf": pxq_total,
        "flete_uf": fle,
        "total_externo_sin_materiales_uf": pxq_total + fle,
    }

# =========================
# 6) FASE 1 – MILP (asigna ciudades a técnicos o externo)
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

    m.x = pyo.Var(m.C, m.T, m.M, domain=pyo.Binary)
    m.y = pyo.Var(m.C, domain=pyo.Binary)  # 1 interno, 0 externo

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

    # lecturas
    tech_cities = {t: [] for t in TECNICOS}
    rows_assign = []
    rows_city_dec = []

    for c in C_REG:
        y = int(pyo.value(m.y[c]) > 0.5)
        ext = costo_externo_uf(c, int(max(0, GPS_TOTAL.get(c, 0))))
        rows_city_dec.append({
            "ciudad": c,
            "gps": int(max(0, GPS_TOTAL.get(c, 0))),
            "y_interno_fase1": y,
            "costo_externo_sin_mat_uf": ext["total_externo_sin_materiales_uf"],
            "pxq_unit_uf_gps": ext["pxq_unit_uf_gps"],
            "flete_uf": ext["flete_uf"],
        })

        for t in TECNICOS:
            for mo in MODOS:
                if pyo.value(m.x[c, t, mo]) > 0.5:
                    tech_cities[t].append(c)
                    rows_assign.append({
                        "ciudad": c,
                        "tecnico": t,
                        "modo": mo,
                        "dias_aprox": int(0 if GPS_TOTAL.get(c, 0) == 0 else 1) if False else None,  # placeholder
                        "costo_interno_aprox_uf": float(costo_interno_aprox_uf(t, c, mo)),
                        "dias_total_aprox": int(dias_total_aprox(t, c, mo)),
                    })

    df_assign = pd.DataFrame(rows_assign)
    df_city_dec = pd.DataFrame(rows_city_dec)

    return {
        "tech_cities": tech_cities,
        "df_assign_fase1": df_assign,
        "df_city_dec_fase1": df_city_dec,
        "model": m,  # por si luego quieres auditar más
    }

# =========================
# 7) FASE 2 – SIMULACIÓN + ASIGNACIÓN FACTIBLE POR DÍAS
# =========================
def simulate_tech_schedule(tecnico: str, cities_list: list[str], gps_asignados: dict[str, int]):
    base = base_tecnico(tecnico)
    hd = horas_diarias(tecnico)
    gpd = gps_por_dia(tecnico)

    if hd <= 1e-9 or gpd <= 0:
        return [], {"total_uf": 1e18}, False, []

    day = 1
    sleep_city = base

    plan = []
    travel_legs = []  # auditoría: cada tramo viajado
    cost = {"travel_uf": 0.0, "aloj_uf": 0.0, "alm_uf": 0.0, "inc_uf": 0.0, "sueldo_uf": 0.0, "flete_uf": 0.0}

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1, DIAS_MAX)

    pending = {c: int(max(0, gps_asignados.get(c, 0))) for c in cities_list}

    def can_install_today(time_left_h: float) -> int:
        return int(math.floor(time_left_h / max(1e-9, TIEMPO_INST_GPS_H)))

    for c in cities_list:
        if pending.get(c, 0) <= 0:
            continue
        if day > DIAS_MAX:
            break

        modo_in = choose_mode(sleep_city, c)
        tv = t_viaje(sleep_city, c, modo_in)
        cv = costo_viaje_uf(sleep_city, c, modo_in)

        travel_legs.append({
            "tecnico": tecnico,
            "from": sleep_city,
            "to": c,
            "modo": modo_in,
            "tv_h": tv,
            "costo_viaje_uf": cv,
            "dia_inicio": day
        })

        cost["travel_uf"] += cv
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia

        if flete_aplica(c, base, modo_in):
            cost["flete_uf"] += safe_float(FLETE_UF.get(c, 0.0), 0.0)

        # Opción A: día solo viaje si tv > hh_día y hay cambio de ciudad
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
            tv = 0.0
            modo_in = None

        time_left = max(0.0, hd - tv)
        gps_can = can_install_today(time_left)
        gps_inst = min(pending[c], gps_can)

        horas_instal = gps_inst * TIEMPO_INST_GPS_H
        pending[c] -= gps_inst
        cost["inc_uf"] += INCENTIVO_UF * gps_inst

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

        while pending[c] > 0 and day <= DIAS_MAX:
            gps_inst = min(pending[c], gpd)
            horas_instal = gps_inst * TIEMPO_INST_GPS_H
            pending[c] -= gps_inst

            cost["alm_uf"] += ALMU_UF
            cost["sueldo_uf"] += sueldo_dia
            cost["inc_uf"] += INCENTIVO_UF * gps_inst
            if sleep_city != base:
                cost["aloj_uf"] += ALOJ_UF

            plan.append({
                "tecnico": tecnico, "dia": day, "ciudad_trabajo": c,
                "horas_instal": horas_instal, "gps_inst": int(gps_inst),
                "viaje_modo_manana": None, "viaje_h_manana": 0.0,
                "duerme_en": sleep_city, "nota": ""
            })
            day += 1

    feasible = (day - 1) <= DIAS_MAX
    cost["total_uf"] = sum(v for k, v in cost.items() if k != "total_uf")
    return plan, cost, feasible, travel_legs

def allocate_gps_work_factible(tech_cities: dict[str, list[str]]):
    """
    Asignación factible por días:
    - Cada técnico: base (si hay demanda) + ciudades asignadas
    - GPS enteros
    - Travel_day si tv>hh_día al cambiar ciudad
    - Retorna también auditoría de días usados por técnico x ciudad
    """
    rem_gps = {c: int(max(0, GPS_TOTAL.get(c, 0))) for c in CIUDADES}
    gps_asignados = {t: defaultdict(int) for t in TECNICOS}
    audit_rows = []

    for t in TECNICOS:
        base = base_tecnico(t)
        gpd = gps_por_dia(t)
        hd = horas_diarias(t)
        if gpd <= 0 or hd <= 1e-9:
            audit_rows.append({
                "tecnico": t, "base": base, "gpd": gpd, "hdia": hd,
                "dias_left_final": DIAS_MAX, "nota": "Sin capacidad (gpd<=0 o hdia<=0)"
            })
            continue

        days_left = DIAS_MAX
        current_city = base

        ordered = []
        if rem_gps.get(base, 0) > 0:
            ordered.append(base)
        ordered += [c for c in tech_cities.get(t, []) if c != base]

        for c in ordered:
            if rem_gps.get(c, 0) <= 0 or days_left <= 0:
                continue

            modo = choose_mode(current_city, c)
            tv = t_viaje(current_city, c, modo)
            travel_day = 1 if (current_city != c and tv > hd) else 0

            if days_left - travel_day <= 0:
                break

            max_install_days = days_left - travel_day
            max_gps = max_install_days * gpd
            take = int(max(0, min(rem_gps[c], max_gps)))

            if take <= 0:
                break

            install_days_used = int(math.ceil(take / max(1, gpd)))

            audit_rows.append({
                "tecnico": t,
                "base": base,
                "from_city": current_city,
                "to_city": c,
                "modo": modo,
                "tv_h": tv,
                "travel_day": travel_day,
                "days_left_before": days_left,
                "install_days_used": install_days_used,
                "gps_take": take,
                "gpd": gpd,
                "hdia": hd,
                "days_left_after": days_left - (travel_day + install_days_used),
            })

            gps_asignados[t][c] += take
            rem_gps[c] -= take
            days_left -= (travel_day + install_days_used)
            current_city = c

            if days_left <= 0:
                break

        audit_rows.append({
            "tecnico": t,
            "base": base,
            "gpd": gpd,
            "hdia": hd,
            "dias_left_final": days_left,
            "nota": "FIN"
        })

    df_audit = pd.DataFrame(audit_rows)
    return gps_asignados, rem_gps, df_audit

def total_cost_solution(tech_cities):
    gps_asignados, rem_gps, _ = allocate_gps_work_factible(tech_cities)
    total = 0.0

    for t in TECNICOS:
        cities = [c for c, g in gps_asignados[t].items() if g > 0]
        if not cities:
            continue
        base = base_tecnico(t)
        if base in cities:
            cities = [base] + [c for c in cities if c != base]

        plan, cst, feas, _legs = simulate_tech_schedule(t, cities, gps_asignados[t])
        if not feas:
            return 1e18
        total += cst["total_uf"]

    for c in CIUDADES:
        gps_ext = int(max(0, rem_gps.get(c, 0)))
        ext = costo_externo_uf(c, gps_externos=gps_ext)
        total += ext["total_externo_sin_materiales_uf"]

    total += sum(costo_materiales_ciudad(c) for c in CIUDADES)
    return total

def improve_solution(tech_cities, iters=400, seed=42):
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
            tc2[t_from].remove(c)

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
# 8) REPORTES (MAX DESGLOSE)
# =========================
def build_reports(tech_cities_final, ws_phase1):
    gps_asignados, rem_gps, df_audit_alloc = allocate_gps_work_factible(tech_cities_final)

    # ---------- Plan diario + costos internos por técnico ----------
    plan_rows = []
    legs_rows = []
    cost_interno_rows = []
    alloc_rows = []

    for t in TECNICOS:
        for c, g in gps_asignados[t].items():
            if g > 0:
                alloc_rows.append({
                    "tecnico": t,
                    "base": base_tecnico(t),
                    "ciudad": c,
                    "gps_asignados_internos": int(g),
                })

    for t in TECNICOS:
        cities = [c for c, g in gps_asignados[t].items() if g > 0]
        if not cities:
            continue
        base = base_tecnico(t)
        if base in cities:
            cities = [base] + [c for c in cities if c != base]

        plan, cst, feas, legs = simulate_tech_schedule(t, cities, gps_asignados[t])
        if not feas:
            raise RuntimeError(f"Solución final infeasible para técnico {t}")

        plan_rows.extend(plan)
        legs_rows.extend(legs)

        gps_int = int(sum(gps_asignados[t].values()))
        cost_interno_rows.append({
            "tecnico": t,
            "base": base,
            "gps_internos_total": gps_int,
            "travel_uf": cst["travel_uf"],
            "aloj_uf": cst["aloj_uf"],
            "alm_uf": cst["alm_uf"],
            "sueldo_uf": cst["sueldo_uf"],
            "inc_uf": cst["inc_uf"],
            "flete_uf": cst["flete_uf"],
            "total_uf": cst["total_uf"],
            "uf_por_gps_interno": (cst["total_uf"] / gps_int) if gps_int > 0 else 0.0
        })

    df_plan = pd.DataFrame(plan_rows)
    if not df_plan.empty:
        df_plan = df_plan.sort_values(["tecnico", "dia"]).reset_index(drop=True)
        df_plan["gps_inst"] = df_plan["gps_inst"].astype(int)
    else:
        df_plan = pd.DataFrame(columns=[
            "tecnico", "dia", "ciudad_trabajo", "horas_instal", "gps_inst",
            "viaje_modo_manana", "viaje_h_manana", "duerme_en", "nota"
        ])

    df_legs = pd.DataFrame(legs_rows)
    df_cost_interno = pd.DataFrame(cost_interno_rows).sort_values("total_uf", ascending=False)
    df_alloc = pd.DataFrame(alloc_rows).sort_values(["tecnico", "ciudad"])

    # ---------- Costos externos por ciudad + materiales ----------
    city_rows = []
    for c in CIUDADES:
        gps_total = int(max(0, GPS_TOTAL.get(c, 0)))
        gps_ext = int(max(0, rem_gps.get(c, 0)))
        gps_int_city = int(max(0, gps_total - gps_ext))

        ext = costo_externo_uf(c, gps_externos=gps_ext)
        mat = costo_materiales_ciudad(c)
        total_city = ext["total_externo_sin_materiales_uf"] + mat  # en esta versión: internos se expresan por técnico

        city_rows.append({
            "ciudad": c,
            "gps_total": gps_total,
            "gps_internos": gps_int_city,
            "gps_externos": gps_ext,
            "pxq_unit_uf_gps": ext["pxq_unit_uf_gps"],
            "pxq_uf": ext["pxq_uf"],
            "flete_uf": ext["flete_uf"],
            "materiales_uf": mat,
            "externo_sin_mat_uf": ext["total_externo_sin_materiales_uf"],
            "total_ciudad_uf": total_city,
            "uf_por_gps_total": (total_city / gps_total) if gps_total > 0 else 0.0,
            "share_pxq": 0.0, "share_flete": 0.0, "share_materiales": 0.0
        })

    df_city = pd.DataFrame(city_rows)
    total_all_city = df_city["total_ciudad_uf"].sum()
    df_city["share_pxq"] = df_city.apply(lambda r: pct(r["pxq_uf"], r["total_ciudad_uf"]), axis=1)
    df_city["share_flete"] = df_city.apply(lambda r: pct(r["flete_uf"], r["total_ciudad_uf"]), axis=1)
    df_city["share_materiales"] = df_city.apply(lambda r: pct(r["materiales_uf"], r["total_ciudad_uf"]), axis=1)
    df_city = df_city.sort_values("total_ciudad_uf", ascending=False)

    # ---------- Pareto / rankings ----------
    pareto_total = df_city[["ciudad", "total_ciudad_uf", "gps_total", "uf_por_gps_total"]].copy()
    pareto_total["cum_uf"] = pareto_total["total_ciudad_uf"].cumsum()
    pareto_total["cum_share"] = pareto_total["cum_uf"] / max(1e-9, pareto_total["total_ciudad_uf"].sum())

    pareto_pxq = df_city.sort_values("pxq_uf", ascending=False)[["ciudad", "pxq_uf", "gps_externos", "pxq_unit_uf_gps"]].copy()
    pareto_mat = df_city.sort_values("materiales_uf", ascending=False)[["ciudad", "materiales_uf", "gps_total"]].copy()
    pareto_flete = df_city.sort_values("flete_uf", ascending=False)[["ciudad", "flete_uf", "gps_externos"]].copy()

    # ---------- Resumen total (incluye internos por técnico) ----------
    total_externo = df_city["externo_sin_mat_uf"].sum()
    total_materiales = df_city["materiales_uf"].sum()
    total_interno = df_cost_interno["total_uf"].sum() if not df_cost_interno.empty else 0.0
    total_uf = total_interno + total_externo + total_materiales

    df_resumen_total = pd.DataFrame([
        ["total_uf", total_uf],
        ["total_interno_uf", total_interno],
        ["total_externo_sin_materiales_uf", total_externo],
        ["materiales_total_uf", total_materiales],
        ["gps_total", sum(int(max(0, GPS_TOTAL.get(c, 0))) for c in CIUDADES)],
        ["gps_internos_total", int(df_city["gps_internos"].sum())],
        ["gps_externos_total", int(df_city["gps_externos"].sum())],
        ["dias_max_proyecto", DIAS_MAX],
        ["dias_semana", DIAS_SEM],
        ["semanas", SEMANAS],
        ["horas_jornada", H_DIA],
        ["tiempo_inst_gps_h", TIEMPO_INST_GPS_H],
        ["incentivo_uf_gps", INCENTIVO_UF],
        ["precio_bencina_uf_km", PRECIO_BENCINA_UF_KM],
        ["nota", "MAX DESGLOSE: internos por técnico + externos por ciudad + materiales. Sin forzar internos."]
    ], columns=["metric", "value"])

    # ---------- Parámetros y capacidad técnicos ----------
    param_rows = []
    for k, v in param.items():
        param_rows.append({"parametro": k, "valor": v})
    df_param = pd.DataFrame(param_rows).sort_values("parametro")

    cap_rows = []
    for t in TECNICOS:
        cap_rows.append({
            "tecnico": t,
            "base": base_tecnico(t),
            "dias_semana_proyecto_input": dias_semana_proyecto(t),
            "horas_semana_proyecto": horas_semana_proyecto(t),
            "hdia": horas_diarias(t),
            "gps_por_dia": gps_por_dia(t),
            "sueldo_proyecto_uf": costo_sueldo_proyecto_uf(t),
            "dias_max_proyecto": DIAS_MAX,
        })
    df_cap = pd.DataFrame(cap_rows).sort_values(["base", "tecnico"])

    # ---------- Auditoría de inputs “de negocio” ----------
    df_pxq_flete = pd.DataFrame([{
        "ciudad": c,
        "pxq_unit_uf_gps": safe_float(PXQ_UF_POR_GPS.get(c), 0.0),
        "flete_uf": safe_float(FLETE_UF.get(c), 0.0),
        "kit_1gps_uf": KIT1_UF,
        "kit_2gps_uf": KIT2_UF,
        "vehiculos_1gps": safe_float(V1.get(c, 0.0), 0.0),
        "vehiculos_2gps": safe_float(V2.get(c, 0.0), 0.0),
        "gps_total": int(max(0, GPS_TOTAL.get(c, 0))),
        "materiales_uf": costo_materiales_ciudad(c),
    } for c in CIUDADES]).sort_values("ciudad")

    df_demanda_det = demanda.copy()

    # ---------- Comparativo interno vs externo (aprox fase 1) ----------
    # Si Fase 1 asigna interno: comparar costo interno aprox vs externo (sin materiales)
    df_city_dec_fase1 = ws_phase1["df_city_dec_fase1"].copy()
    df_assign_fase1 = ws_phase1["df_assign_fase1"].copy()

    if not df_assign_fase1.empty:
        # para cada ciudad, tomar el registro asignado (ciudad -> tecnico/modo/costo)
        df_best = df_assign_fase1.sort_values("costo_interno_aprox_uf").groupby("ciudad", as_index=False).first()
        df_comp = df_city_dec_fase1.merge(df_best[["ciudad", "tecnico", "modo", "costo_interno_aprox_uf", "dias_total_aprox"]],
                                          on="ciudad", how="left")
    else:
        df_comp = df_city_dec_fase1.copy()
        df_comp["tecnico"] = None
        df_comp["modo"] = None
        df_comp["costo_interno_aprox_uf"] = np.nan
        df_comp["dias_total_aprox"] = np.nan

    df_comp["delta_interno_menos_externo_uf"] = df_comp["costo_interno_aprox_uf"] - df_comp["costo_externo_sin_mat_uf"]
    df_comp["preferencia_aprox"] = df_comp.apply(
        lambda r: "INTERNO(aprox)" if pd.notna(r["delta_interno_menos_externo_uf"]) and r["delta_interno_menos_externo_uf"] < 0 else "EXTERNO(aprox)",
        axis=1
    )
    df_comp = df_comp.sort_values("delta_interno_menos_externo_uf", ascending=True)

    # ---------- Costos detalle (tabla “contable”) ----------
    cost_rows = []

    # internos por técnico (si existen)
    for _, r in df_cost_interno.iterrows():
        cost_rows.append({
            "responsable": r["tecnico"],
            "tipo": "INTERNO",
            "travel_uf": r["travel_uf"],
            "aloj_uf": r["aloj_uf"],
            "alm_uf": r["alm_uf"],
            "sueldo_uf": r["sueldo_uf"],
            "inc_uf": r["inc_uf"],
            "flete_uf": r["flete_uf"],
            "pxq_uf": 0.0,
            "materiales_uf": 0.0,
            "total_uf": r["total_uf"],
        })

    # externos por ciudad
    for _, r in df_city.iterrows():
        cost_rows.append({
            "responsable": r["ciudad"],
            "tipo": "EXTERNO",
            "travel_uf": 0.0,
            "aloj_uf": 0.0,
            "alm_uf": 0.0,
            "sueldo_uf": 0.0,
            "inc_uf": 0.0,
            "flete_uf": r["flete_uf"],
            "pxq_uf": r["pxq_uf"],
            "materiales_uf": 0.0,
            "total_uf": r["externo_sin_mat_uf"],
        })

    # materiales (línea auditora)
    cost_rows.append({
        "responsable": "MATERIALES (TOTAL)",
        "tipo": "MATERIALES",
        "travel_uf": 0.0,
        "aloj_uf": 0.0,
        "alm_uf": 0.0,
        "sueldo_uf": 0.0,
        "inc_uf": 0.0,
        "flete_uf": 0.0,
        "pxq_uf": 0.0,
        "materiales_uf": total_materiales,
        "total_uf": total_materiales,
    })

    df_cost = pd.DataFrame(cost_rows).sort_values(["tipo", "total_uf"], ascending=[True, False])

    return {
        "Resumen_Total": df_resumen_total,
        "Costos_por_Ciudad": df_city,
        "Pareto_Total": pareto_total,
        "Pareto_PXQ": pareto_pxq,
        "Pareto_Materiales": pareto_mat,
        "Pareto_Flete": pareto_flete,
        "Costos_Internos_Tecnico": df_cost_interno,
        "Asignacion_GPS_Tecnico_Ciudad": df_alloc,
        "Auditoria_Asignacion_Dias": df_audit_alloc,
        "Plan_Diario": df_plan,
        "Auditoria_Viajes": df_legs,
        "Costos_Detalle_Contable": df_cost,
        "Parametros_Usados": df_param,
        "Capacidad_Tecnicos": df_cap,
        "Input_PXQ_Flete_Kits_Demanda": df_pxq_flete,
        "Demanda_Detalle": df_demanda_det,
        "Fase1_Asignaciones": ws_phase1["df_assign_fase1"],
        "Fase1_Ciudad_Decision": ws_phase1["df_city_dec_fase1"],
        "Fase1_Comparativo_Int_vs_Ext": df_comp,
    }

# =========================
# 9) RUN + EXPORT (MAX)
# =========================
def run_all():
    print(f"[INFO] CBC_EXE = {CBC_EXE}")
    print(f"[INFO] DIAS_MAX={DIAS_MAX} DIAS_SEM={DIAS_SEM} SEMANAS={SEMANAS} H_DIA={H_DIA} TIEMPO_INST={TIEMPO_INST_GPS_H}")
    print(f"[INFO] INCENTIVO_UF={INCENTIVO_UF} PRECIO_BENCINA_UF_KM={PRECIO_BENCINA_UF_KM}")

    # DEBUG capacidad
    print("\n=== DEBUG CAPACIDAD INTERNOS (AUDIT) ===")
    for t in TECNICOS:
        print(
            f"- {t:20s} base={base_tecnico(t):12s} "
            f"dias_sem_proy={dias_semana_proyecto(t):6.2f} "
            f"hdia={horas_diarias(t):6.2f} gps/dia={gps_por_dia(t):3d} "
            f"sueldo_proy_uf={costo_sueldo_proyecto_uf(t):8.2f}"
        )

    ws1 = solve_phase1()
    tech_cities = ws1["tech_cities"]

    # mejora (sin forzar)
    tech_cities2, best_cost = improve_solution(tech_cities, iters=400, seed=42)

    reports = build_reports(tech_cities2, ws1)

    out_path = os.path.join(OUTPUTS_DIR, "plan_global_operativo_MAX_DESGLOSE.xlsx")
    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        # Orden pensado para comité + data room
        order = [
            "Resumen_Total",
            "Costos_por_Ciudad",
            "Pareto_Total",
            "Pareto_PXQ",
            "Pareto_Materiales",
            "Pareto_Flete",
            "Costos_Internos_Tecnico",
            "Asignacion_GPS_Tecnico_Ciudad",
            "Auditoria_Asignacion_Dias",
            "Plan_Diario",
            "Auditoria_Viajes",
            "Costos_Detalle_Contable",
            "Fase1_Comparativo_Int_vs_Ext",
            "Fase1_Asignaciones",
            "Fase1_Ciudad_Decision",
            "Capacidad_Tecnicos",
            "Parametros_Usados",
            "Input_PXQ_Flete_Kits_Demanda",
            "Demanda_Detalle",
        ]
        for name in order:
            df = reports.get(name)
            if df is None:
                continue
            df.to_excel(w, index=False, sheet_name=name[:31])  # Excel limita a 31 chars

    # resumen consola
    df_res = reports["Resumen_Total"]
    total_uf = float(df_res.loc[df_res["metric"] == "total_uf", "value"].values[0])
    print("[OK] ->", out_path)
    print("[OK] Costo total (UF):", round(total_uf, 4))
    print("[OK] best_cost evaluator (UF):", round(best_cost, 4))

if __name__ == "__main__":
    run_all()
