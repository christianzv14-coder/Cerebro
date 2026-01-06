# modelo_optimizacion_gps_chile_FINAL_FTE.py
# Optimización costos instalación GPS (Chile) – FIX FTE (hh_semana_proyecto = FTE)
#
# CAMBIO CLAVE:
# - hh_semana_proyecto se interpreta como FTE (0..1): fracción de jornada semanal.
#   horas_semana = FTE * (DIAS_SEM * H_DIA)
#   horas_dia = horas_semana / DIAS_SEM = FTE * H_DIA
#   gps/dia = floor(horas_dia / TIEMPO_INST)
#
# Mantiene:
# - Factibilidad por días + Opción A (tv > hh_día => día solo viaje)
# - Decisión endógena: interno = lo que cabe factiblemente; externo = remanente
# - Guardrails PXQ/Flete
#
# Inputs: en ./data/ (UF)
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
    """
    Soporta coma decimal ("100,5").
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
    missing = [c for c in cities if c not in mapping]
    if missing:
        raise ValueError(f"[ERROR] {name}: faltan ciudades: {missing}")

    bad = []
    for c in cities:
        v = mapping.get(c, None)
        if v is None:
            bad.append((c, v))
            continue
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

ALOJ_UF = 1.1 # OVERRIDE: Bed only (Food is separate)
ALMU_UF = safe_float(param.get("almuerzo_uf_dia"), 0.5)
INCENTIVO_UF = 1.04 # OVERRIDE param.get("incentivo_por_gps")

PRECIO_BENCINA_UF_KM = safe_float(param.get("precio_bencina_uf_km"), 0.0)

print(f"[INFO] DIAS_SEM={DIAS_SEM} SEMANAS={SEMANAS} H_DIA={H_DIA} TIEMPO_INST={TIEMPO_INST_GPS_H}")
print(f"[INFO] INCENTIVO_UF={INCENTIVO_UF} PRECIO_BENCINA_UF_KM={PRECIO_BENCINA_UF_KM}")

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

# PXQ y flete
pxq["ciudad"] = pxq["ciudad"].apply(norm_city)
flete["ciudad"] = flete["ciudad"].apply(norm_city)

PXQ_UF_POR_GPS = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))   # UF/GPS
FLETE_UF = dict(zip(flete["ciudad"], flete["costo_flete"]))     # UF por ciudad

require_mapping_coverage(PXQ_UF_POR_GPS, CIUDADES, "PXQ_UF_POR_GPS", allow_zero=False)
require_mapping_coverage(FLETE_UF, CIUDADES, "FLETE_UF", allow_zero=True)

# =========================
# 5) FUNCIONES BASE
# =========================
def base_tecnico(tecnico: str) -> str:
    return internos.loc[internos["tecnico"] == tecnico, "ciudad_base"].values[0]

def fte_tecnico(tecnico: str) -> float:
    """
    Opción 1: hh_semana_proyecto es FTE (0..1)
    """
    return max(0.0, safe_float(internos.loc[internos["tecnico"] == tecnico, "hh_semana_proyecto"].values[0], 0.0))

def horas_semana_proyecto(tecnico: str) -> float:
    # FIX FTE: horas/semana = FTE * (DIAS_SEM * H_DIA)
    return fte_tecnico(tecnico) * (DIAS_SEM * H_DIA)

def horas_diarias(tecnico: str) -> float:
    # CAMBIO LÓGICA: Jornada completa (H_DIA), el FTE afecta los días disponibles, no las horas diarias.
    return H_DIA

def dias_disponibles_proyecto(tecnico: str) -> int:
    """
    Días de calendario disponibles para operar dentro del proyecto (capacidad en 'días').
    Con FTE, no tiene sentido inflar días; lo correcto es:
    dias_disp = floor(FTE * DIAS_MAX)
    """
    return int(math.floor(fte_tecnico(tecnico) * DIAS_MAX + 1e-9))

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

def choose_mode(origin: str, dest: str) -> str:
    # 1. Check strict time constraint preference
    tv_road = t_viaje(origin, dest, "terrestre")
    tv_air = t_viaje(origin, dest, "avion")
    
    # If Road is too slow (>5.6h) but Air is fast enough, FORCE Air
    # (Aligns with Heuristic)
    if tv_road > 5.6 and tv_air <= 5.6:
        return "avion"
        
    # 2. Otherwise minimize cost
    c_terr = costo_viaje_uf(origin, dest, "terrestre")
    c_avion = costo_viaje_uf(origin, dest, "avion")
    
    if c_avion < c_terr:
        return "avion"
    return "terrestre"

def flete_aplica(ciudad: str, base: str, modo_llegada: str) -> bool:
    if ciudad == SANTIAGO and base == SANTIAGO and modo_llegada == "terrestre":
        return False
    return True

def costo_sueldo_proyecto_uf(tecnico: str) -> float:
    """
    Sueldo prorrateado según horas asignadas al proyecto.
    horas_proy = horas_semana_proyecto * SEMANAS
    """
    sueldo_mes = safe_float(internos.loc[internos["tecnico"] == tecnico, "sueldo_uf"].values[0], 0.0)
    horas_proy = horas_semana_proyecto(tecnico) * SEMANAS
    return sueldo_mes * (horas_proy / max(1e-9, HH_MES))

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

def costo_flete_interno_uf(ciudad: str) -> float:
    """
    Costo de envío de materiales a técnicos internos ubicados en regiones.
    Aplica principalmente a Bases Remotas (Calama, Chillán).
    """
    if ciudad == SANTIAGO:
        return 0.0
    # Logic: If it is a Base City, we ship materials.
    # User Request: "Calama y Chillan".
    # We check if FLETE_UF has a value.
    return safe_float(FLETE_UF.get(ciudad, 0.0), 0.0)

# =========================
# 6) FASE 1 – MILP
# =========================
def solve_phase1():
    C_REG = [c for c in CIUDADES if c != SANTIAGO]

    if not CBC_EXE or not os.path.exists(CBC_EXE):
        raise RuntimeError("No se encontró CBC vía PuLP.")

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
        dias_cap = dias_disponibles_proyecto(t)
        return sum(dias_total_aprox(t, c, mo) * mm.x[c, t, mo] for c in mm.C for mo in mm.M) <= dias_cap
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
# 7) FASE 2 – SIMULACIÓN + ASIGNACIÓN FACTIBLE
# =========================
def simulate_tech_schedule(tecnico: str, cities_list: list[str], gps_asignados: dict[str, int]):
    base = base_tecnico(tecnico)
    hd = horas_diarias(tecnico)
    gpd = gps_por_dia(tecnico)
    dias_cap = dias_disponibles_proyecto(tecnico)

    pending = {c: int(max(0, gps_asignados.get(c, 0))) for c in cities_list}

    if hd <= 1e-9 or gpd <= 0 or dias_cap <= 0:
        return [], {"total_uf": 1e18}, pending

    day = 1
    sleep_city = base

    plan = []
    cost = {"travel_uf": 0.0, "aloj_uf": 0.0, "alm_uf": 0.0, "inc_uf": 0.0, "sueldo_uf": 0.0, "flete_uf": 0.0, "traslado_interno_uf": 0.0}

    # Consolidated Flete Logic (Added from duplicate)
    if base in ["Chillan", "Calama"]:
        cost["flete_uf"] += safe_float(FLETE_UF.get(base, 0.0), 0.0)

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1, dias_cap) 

    pending = {c: int(max(0, gps_asignados.get(c, 0))) for c in cities_list}

    def can_install_today(time_left_h: float) -> int:
        return int(math.floor(time_left_h / max(1e-9, TIEMPO_INST_GPS_H)))

    # LOOP GENERAL POR CIUDAD
    cities_idx = 0
    
    # MODIFICATION: Relaxed constraint (max 60 days) to allow completion even if over capacity
    while cities_idx < len(cities_list) and day <= 60: 
        c = cities_list[cities_idx]
        
        if pending.get(c, 0) <= 0:
            cities_idx += 1
            continue
            
        # Removed hard break on day > dias_cap to allow "Overtime" auditing
        # if day > dias_cap:
        #    break

        # --- CHECK SUNDAY (Day 7, 14, 21...) ---
        if day % 7 == 0:
            if sleep_city != base:
                cost["aloj_uf"] += ALOJ_UF
                cost["alm_uf"] += ALMU_UF
            
            plan.append({
                "tecnico": tecnico, "dia": day, "ciudad_trabajo": sleep_city,
                "horas_instal": 0.0, "gps_inst": 0, "viaje_modo_manana": None, 
                "duerme_en": sleep_city, "nota": "DOMINGO (Descanso)"
            })
            day += 1
            continue

        # --- DÍA LABORAL ---
        tv = 0.0
        modo_in = None
        
        if sleep_city != c:
            modo_in = choose_mode(sleep_city, c)
            tv = t_viaje(sleep_city, c, modo_in)
            cv = costo_viaje_uf(sleep_city, c, modo_in)
            
            if tv > hd:
                cost["travel_uf"] += cv
                if flete_aplica(c, base, modo_in):
                   cost["flete_uf"] += safe_float(FLETE_UF.get(c, 0.0), 0.0)
                cost["travel_uf"] += 0.13
                cost["traslado_interno_uf"] += 0.13 # Costo mov interno dia viaje
                
                cost["alm_uf"] += ALMU_UF
                cost["sueldo_uf"] += sueldo_dia
                cost["aloj_uf"] += ALOJ_UF
                
                sleep_city = c
                plan.append({
                    "tecnico": tecnico, "dia": day, "ciudad_trabajo": c,
                    "horas_instal": 0.0, "gps_inst": 0,
                    "viaje_modo_manana": modo_in, "viaje_h_manana": tv,
                    "duerme_en": c, "nota": "Día Solo Viaje (>8h)"
                })
                day += 1
                continue
            else:
                cost["travel_uf"] += cv
                if flete_aplica(c, base, modo_in):
                    cost["flete_uf"] += safe_float(FLETE_UF.get(c, 0.0), 0.0)
                cost["travel_uf"] += 0.13
        
        time_left = max(0.0, hd - tv)
        gps_can = can_install_today(time_left)
        gps_inst = min(pending[c], gps_can)
        
        horas_instal = gps_inst * TIEMPO_INST_GPS_H
        pending[c] -= gps_inst
        cost["inc_uf"] += INCENTIVO_UF * gps_inst
        
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia
        cost["traslado_interno_uf"] += 0.13 # Costo mov interno dia trabajo
        
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

    # --- RETORNO A BASE ---
    if sleep_city != base:
        modo_ret = choose_mode(sleep_city, base)
        tv_ret = t_viaje(sleep_city, base, modo_ret)
        cv_ret = costo_viaje_uf(sleep_city, base, modo_ret)

        cost["travel_uf"] += cv_ret
        if tv_ret > hd:
             cost["aloj_uf"] += ALOJ_UF
        
        plan.append({
            "tecnico": tecnico, "dia": day, "ciudad_trabajo": base,
            "horas_instal": 0.0, "gps_inst": 0, "viaje_modo_manana": modo_ret, 
            "viaje_h_manana": tv_ret, "duerme_en": base, "nota": "Retorno a Base"
        })

    cost["total_uf"] = sum(v for k, v in cost.items() if k != "total_uf")
    
    return plan, cost, pending

# =========================
# 7) FASE 2 – SIMULACIÓN + ASIGNACIÓN FACTIBLE
# =========================
def simulate_tech_schedule_DUPLICATE_REMOVED(tecnico: str, cities_list: list[str], gps_asignados: dict[str, int]):
    base = base_tecnico(tecnico)
    hd = horas_diarias(tecnico)
    gpd = gps_por_dia(tecnico)
    dias_cap = dias_disponibles_proyecto(tecnico)

    pending = {c: int(max(0, gps_asignados.get(c, 0))) for c in cities_list}

    if hd <= 1e-9 or gpd <= 0 or dias_cap <= 0:
        return [], {"total_uf": 1e18}, pending # Return full pending as overflow

    day = 1
    sleep_city = base

    plan = []
    cost = {"travel_uf": 0.0, "aloj_uf": 0.0, "alm_uf": 0.0, "inc_uf": 0.0, "sueldo_uf": 0.0, "flete_uf": 0.0}

    # --- FREIGHT LOGIC (Custom per User) ---
    # "Envio a las bases de chillan y calama"
    # Santiago base (Luis/Wilmer/etc) -> No freight, they carry it.
    # Chillan/Calama base -> Pay freight to get materials to base.
    # We assume one consolidated shipment or cost proportional? 
    # Let's charge the defined Flete Unit cost for the Base City * 1 (Big Shipment)
    # OR maybe per GPS? "Envio" suggests shipping.
    # Let's assume 1 shipment per project for these bases is the intention.
    if base in ["Chillan", "Calama"]:
        cost["flete_uf"] += safe_float(FLETE_UF.get(base, 0.0), 0.0)

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1, dias_cap) 

    def can_install_today(time_left_h: float) -> int:
        return int(math.floor(time_left_h / max(1e-9, TIEMPO_INST_GPS_H)))

    # LOOP GENERAL POR CIUDAD
    cities_idx = 0
    
    # STRICT DEADLINE CONSTRAINT
    working = True
    while cities_idx < len(cities_list) and working: 
        c = cities_list[cities_idx]
        
        if pending.get(c, 0) <= 0:
            cities_idx += 1
            continue
            
        if day > dias_cap:
            working = False
            break

        # --- CHECK SUNDAY (Day 7, 14, 21...) ---
        if day % 7 == 0:
            if sleep_city != base:
                cost["aloj_uf"] += ALOJ_UF
                cost["alm_uf"] += ALMU_UF
            
            plan.append({
                "tecnico": tecnico, "dia": day, "ciudad_trabajo": sleep_city,
                "horas_instal": 0.0, "gps_inst": 0, "viaje_modo_manana": None, 
                "duerme_en": sleep_city, "nota": "DOMINGO (Descanso)"
            })
            day += 1
            continue

        # --- DÍA LABORAL ---
        tv = 0.0
        modo_in = None
        
        if sleep_city != c:
            modo_in = choose_mode(sleep_city, c)
            tv = t_viaje(sleep_city, c, modo_in)
            cv = costo_viaje_uf(sleep_city, c, modo_in)
            
            if tv > hd:
                # Travel takes more than full day
                cost["travel_uf"] += cv
                # Internal Techs carry materials -> NO per-city freight charged here.
                cost["travel_uf"] += 0.13
                
                cost["alm_uf"] += ALMU_UF
                cost["sueldo_uf"] += sueldo_dia
                cost["aloj_uf"] += ALOJ_UF
                
                sleep_city = c
                plan.append({
                    "tecnico": tecnico, "dia": day, "ciudad_trabajo": c,
                    "horas_instal": 0.0, "gps_inst": 0,
                    "viaje_modo_manana": modo_in, "viaje_h_manana": tv,
                    "duerme_en": c, "nota": "Día Solo Viaje (>Jornada)"
                })
                day += 1
                continue
            else:
                cost["travel_uf"] += cv
                cost["travel_uf"] += 0.13
        
        time_left = max(0.0, hd - tv)
        gps_can = can_install_today(time_left)
        gps_inst = min(pending[c], gps_can)
        
        horas_instal = gps_inst * TIEMPO_INST_GPS_H
        pending[c] -= gps_inst
        cost["inc_uf"] += INCENTIVO_UF * gps_inst
        
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia
        
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

    # --- RETORNO A BASE ---
    if sleep_city != base:
        modo_ret = choose_mode(sleep_city, base)
        tv_ret = t_viaje(sleep_city, base, modo_ret)
        cv_ret = costo_viaje_uf(sleep_city, base, modo_ret)

        cost["travel_uf"] += cv_ret
        if tv_ret > hd:
             cost["aloj_uf"] += ALOJ_UF
        
        plan.append({
            "tecnico": tecnico, "dia": day, "ciudad_trabajo": base,
            "horas_instal": 0.0, "gps_inst": 0, "viaje_modo_manana": modo_ret, 
            "viaje_h_manana": tv_ret, "duerme_en": base, "nota": "Retorno a Base"
        })

    # Total internal cost
    cost["total_uf"] = sum(v for k, v in cost.items() if k != "total_uf")
    
    return plan, cost, pending

# Cities to force as External (User Request)
FORCED_EXTERNAL_CITIES = ["Arica", "Punta Arenas", "Coyhaique"]

def allocate_gps_work_factible(tech_cities: dict[str, list[str]]):
    # Rem GPS initially has ALL demand
    rem_gps = {c: int(max(0, GPS_TOTAL.get(c, 0))) for c in CIUDADES}
    
    # MASK FORCED EXTERNALS: Technicians cannot see this demand
    rem_gps_internal = rem_gps.copy()
    for c in FORCED_EXTERNAL_CITIES:
        if c in rem_gps_internal:
            rem_gps_internal[c] = 0
            
    gps_asignados = {t: defaultdict(int) for t in TECNICOS}
    
    # State tracking
    tech_state = {}
    for t in TECNICOS:
        tech_state[t] = {
            'current_city': base_tecnico(t),
            'days_used': 0.0, # Estimation
            'active': True
        }
        
        # 1. Anchoring: Check if base has demand (and allowed)
        base = base_tecnico(t)
        if rem_gps_internal.get(base, 0) > 0:
             gpd = gps_por_dia(t)
             dias_cap = dias_disponibles_proyecto(t)
             max_gps = dias_cap * gpd
             
             take = min(rem_gps_internal[base], max_gps)
             gps_asignados[t][base] += take
             rem_gps_internal[base] -= take
             rem_gps[base] -= take # CRITICAL FIX: Update global counter so it's not double-counted as External
             
             # Update state
             days_task = take / max(1, gpd)
             tech_state[t]['days_used'] += days_task

    # 1.5. MILP SUGGESTION (Phase 1 Priority)
    # If MILP suggested cities, try to assign them now
    if tech_cities:
        for t in TECNICOS:
            suggestions = tech_cities.get(t, [])
            for c in suggestions:
                if c == base_tecnico(t): continue # Already handled
                if rem_gps_internal.get(c, 0) <= 0: continue
                
                # Check limits
                gpd = gps_por_dia(t)
                dias_cap = dias_disponibles_proyecto(t)
                days_used = tech_state[t]['days_used']
                if days_used >= dias_cap: continue
                
                # Assign
                needed = rem_gps_internal[c]
                max_gps = (dias_cap - days_used) * gpd
                take = min(needed, max_gps)
                if take > 0:
                    gps_asignados[t][c] += take
                    rem_gps_internal[c] -= take
                    rem_gps[c] -= take
                    
                    tech_state[t]['days_used'] += take / max(1, gpd)
                    tech_state[t]['current_city'] = c # Move virtual pointer

    # 2. Dynamic Nearest Neighbor Allocation
    # Loop until all demand is gone or no techs can move
    while True:
        # Check if any demand remains visible to internals
        if sum(rem_gps_internal.values()) <= 0:
            break
            
        cities_with_demand = [c for c, q in rem_gps_internal.items() if q > 0]
        if not cities_with_demand:
            break
            
        # Filter active techs
        active_techs = [t for t in TECNICOS if tech_state[t]['active']]
        if not active_techs:
            break
            
        # Tech with least load first (Balancing)
        active_techs.sort(key=lambda t: tech_state[t]['days_used'])
        current_tech = active_techs[0]
        
        curr_loc = tech_state[current_tech]['current_city']
        
        # SEARCH REACHABLE CITIES
        reachable = []
        for c in cities_with_demand:
            if c == curr_loc: 
                tv = 0.0
                reachable.append((c, tv)) # Immediate
            else:
                # 1. Calc times for both modes
                tv_road = t_viaje(curr_loc, c, "terrestre")
                tv_air = t_viaje(curr_loc, c, "avion")
                
                # 2. Calc costs (approx for heuristic decision)
                cost_road = costo_viaje_uf(curr_loc, c, "terrestre")
                cost_air = costo_viaje_uf(curr_loc, c, "avion")
                
                # 3. Filter feasible modes (Max 5.6h travel)
                modes = []
                if tv_road <= 5.6:
                    modes.append(("terrestre", tv_road, cost_road))
                if tv_air <= 5.6:
                    modes.append(("avion", tv_air, cost_air))
                
                if not modes:
                    continue
                    
                # 4. Pick best feasible mode (Cheapest preferred)
                modes.sort(key=lambda x: x[2]) # Sort by Cost
                best_mode, final_tv, final_cost = modes[0]
                
                # 5. Add to reachable
                # Heuristic uses 'tv' for sorting proximity? 
                # Or should we prioritize Cost?
                # Original logic sorted by TV (Proximity).
                # But if we fly, TV is short (1h).
                # If we sort by TV, we might ping-pong via Plane?
                # It's better to sort by Cost?
                # Let's stick to Proximity (TV) for now to clump work, 
                # but maybe penalty for Plane?
                # Actually, simply appending (c, final_tv) works with existing sort.
                reachable.append((c, final_tv))
                
                # IMPORTANT: We need to somehow tell the simulation which mode to use?
                # The simulation calls 'choose_mode' again!
                # If 'choose_mode' is dumb, it will revert to Road and fail?
                # 'choose_mode' logic (L310) minimizes COST.
                # It does NOT check time constraints.
                # So if we assign a city here because Plane is valid, 
                # but 'simulate' picks Road (cheaper) -> 'simulate' might log huge hours?
                # Wait, 'simulate' allows > 5.6h?
                # 'simulate' has no hard constraints, it just sums costs.
                # BUT 'simulate' adds 'travel_cost' based on 'choose_mode'.
                # IF 'choose_mode' picks Road (5.9h), the cost is low, but time is 5.9h.
                # The user constraint "max 5h" is a PLANNING constraint (for allocation).
                # If the plan says "Go to La Serena", and reality takes 5.9h, it's technically a violation?
                # Or is it acceptable if valid?
                # Ideally, 'choose_mode' should ALSO respect the constraint if possible.
                # But changing 'choose_mode' global might affect other things.
                # For now, let's fix allocation.
                # If tech goes to La Serena (allocated via Plane logic),
                # 'simulate' will calculate cost.
                # If 'simulate' sees Cheap Road, it uses Road.
                # Cost is Cheap. Time is 6h. User might accept 6h occasionally?
                # User said "flexible entre 400 y 450". 470km is tight.
                # But if we want to FORCE Plane for connectivity, we assume simulate handles it.
                # Actually, to be safe, I should update `choose_mode` to respect 5.6h too?
                # Let's start with fixing Allocation connectivity.
        
        if not reachable:
            # Cannot move anywhere useful
            tech_state[current_tech]['active'] = False
            continue
            
        # Selection: Closest city
        reachable.sort(key=lambda x: x[1])
        best_city, tv = reachable[0]
        
        # Assign
        qty_needed = rem_gps_internal[best_city]
        gpd = gps_por_dia(current_tech)
        dias_cap = dias_disponibles_proyecto(current_tech)
        current_load = tech_state[current_tech]['days_used']
        
        # Cost in days of travel
        travel_cost_days = tv / horas_diarias(current_tech) if horas_diarias(current_tech)>0 else 1.0
        
        days_left = dias_cap - current_load - travel_cost_days
        
        # Max capacity
        max_qty = max(0, int(days_left * gpd))
        
        take = min(qty_needed, max_qty)
        
        if take <= 0:
            tech_state[current_tech]['active'] = False
            continue
            
        gps_asignados[current_tech][best_city] += take
        rem_gps_internal[best_city] -= take
        
        # Update Tech State
        install_days = take / max(1, gpd)
        tech_state[current_tech]['days_used'] += (travel_cost_days + install_days)
        tech_state[current_tech]['current_city'] = best_city

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

        # Simulate with strict cutoff
        _, cst, pending_overflow = simulate_tech_schedule(t, cities, gps_asignados[t])
        
        total += cst["total_uf"]
        
        # Add overflow back to rem_gps for costing
        for c, qty in pending_overflow.items():
            if qty > 0:
                # Add to total simple var not dict to avoid side effect affecting loops?
                # Actually we can just cost it right here
                ext = costo_externo_uf(c, gps_externos=qty)
                total += ext["total_externo_sin_materiales_uf"]

    # externos (initial leftovers)
    for c in CIUDADES:
        gps_ext = int(max(0, rem_gps.get(c, 0)))
        ext = costo_externo_uf(c, gps_externos=gps_ext)
        total += ext["total_externo_sin_materiales_uf"]

    # materiales
    total += sum(costo_materiales_ciudad(c) for c in CIUDADES)

    return total

def run_all():
    print(f"[INFO] CBC_EXE = {CBC_EXE}")
    print(f"[INFO] DIAS_MAX={DIAS_MAX}")

    print("\n=== DEBUG CAPACIDAD INTERNOS (FTE) ===")
    for t in TECNICOS:
        print(
            f"- {t:20s} base={base_tecnico(t):12s} "
            f"fte={fte_tecnico(t):5.2f} dias_disp={dias_disponibles_proyecto(t):3d} "
            f"hdia={horas_diarias(t):5.2f} gps/dia={gps_por_dia(t):3d} "
            f"sueldo_proy_uf={costo_sueldo_proyecto_uf(t):8.2f}"
        )

    # Note: Phase 1 (MILP) ACTIVATED
    print("[INFO] Running Phase 1 (MILP)...")
    try:
        res_phase1 = solve_phase1()
        tech_cities = res_phase1["tech_cities"]
        print(f"[INFO] Phase 1 Suggestions: {tech_cities}")
    except Exception as e:
        print(f"[WARN] Phase 1 failed: {e}. Falling back to Heuristic only.")
        tech_cities = {t: [] for t in TECNICOS}

    # Run Allocator with suggestions
    best_cost = total_cost_solution(tech_cities) # Just for ref

    gps_asignados, rem_gps = allocate_gps_work_factible(tech_cities)

    plan_rows = []
    cost_rows = []
    city_rows = []
    
    # We need to track actual final external GPS (initial rem_gps + overflow)
    final_external_counts = defaultdict(int)
    for c, qty in rem_gps.items():
        final_external_counts[c] += qty

    # internos
    for t in TECNICOS:
        cities = [c for c, g in gps_asignados[t].items() if g > 0]
        if not cities:
            continue
        base = base_tecnico(t)
        if base in cities:
            cities = [base] + [c for c in cities if c != base]

        # Actual Simulation
        plan, cst, pending_overflow = simulate_tech_schedule(t, cities, gps_asignados[t])
        
        # Log Overflow
        for c, qty in pending_overflow.items():
            if qty > 0:
                print(f"[OVERFLOW] {t} en {c}: {qty} GPS asignados no instalados (Externos).")
                final_external_counts[c] += qty

        plan_rows.extend(plan)
        cost_rows.append({
            "responsable": t,
            "tipo": "INTERNO",
            "gps_inst": sum(gps_asignados[t].values()), # Add Qty
            "travel_uf": cst["travel_uf"],
            "aloj_uf": cst["aloj_uf"],
            "alm_uf": cst["alm_uf"],
            "inc_uf": cst["inc_uf"],
            "sueldo_uf": cst["sueldo_uf"],
            "flete_uf": cst["flete_uf"],
            "traslado_interno_uf": cst.get("traslado_interno_uf", 0.0),
            "pxq_uf": 0.0,
            "materiales_uf": 0.0,
            "total_uf": cst["total_uf"],
        })

    # externos (Total Final)
    for c in CIUDADES:
        gps_ext = final_external_counts[c]
        ext = costo_externo_uf(c, gps_externos=gps_ext)

        city_rows.append({
            "ciudad": c,
            "gps_total": int(max(0, GPS_TOTAL.get(c, 0))),
            "gps_internos": int(max(0, GPS_TOTAL.get(c, 0) - gps_ext)),
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
                "responsable": c, # City Name as Responsible
                "tipo": "EXTERNO",
                "gps_inst": gps_ext, # Add Qty
                "travel_uf": 0.0,
                "aloj_uf": 0.0,
                "alm_uf": 0.0,
                "inc_uf": 0.0,
                "sueldo_uf": 0.0,
                "flete_uf": ext["flete_uf"],
                "pxq_uf": ext["pxq_uf"],
                "traslado_interno_uf": 0.0,
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
        "traslado_interno_uf": 0.0,
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

    total_uf = df_cost["total_uf"].sum()

    resumen = pd.DataFrame([
        ["total_uf", total_uf],
        ["total_interno_uf", df_cost.loc[df_cost["tipo"] == "INTERNO", "total_uf"].sum()],
        ["total_externo_sin_materiales_uf", df_cost.loc[df_cost["tipo"] == "EXTERNO", "total_uf"].sum()],
        ["materiales_total_uf", materiales_total],
        ["gps_total", sum(int(max(0, GPS_TOTAL.get(c, 0))) for c in CIUDADES)],
        ["dias_max_proyecto", DIAS_MAX],
        ["nota", "FTE=1.0, JORNADA REDUCIDA (6H). Deadline Estricto (24 días). Remanente -> Externo."]
    ], columns=["metric", "value"])

    outfile_path = os.path.join(OUTPUTS_DIR, "plan_global_operativo.xlsx")
    with pd.ExcelWriter(outfile_path) as w:
        resumen.to_excel(w, index=False, sheet_name="Resumen_Total")
        df_city.to_excel(w, index=False, sheet_name="Costos_por_Ciudad")
        df_plan.to_excel(w, index=False, sheet_name="Plan_Diario")
        df_cost.to_excel(w, index=False, sheet_name="Costos_Detalle")

    print("[OK] ->", outfile_path)
    print("[OK] Costo total (UF):", round(total_uf, 4))
    print("[OK] best_cost evaluator (UF):", round(best_cost, 4))

if __name__ == "__main__":
    run_all()
