# modelo_optimizacion_gps_chile_v7_FINAL.py
# Optimización costos instalación GPS Chile (FINAL)
#
# FIXES CLAVE:
# 1) Entradas 100% UF (NO conversiones CLP/UF).
# 2) PXQ externo es UF POR GPS (se multiplica por GPS_total ciudad).
# 3) Materiales incluidos (UF por GPS según 1_GPS y 2_GPS).
# 4) Santiago MIXTO (interno + externo en la misma ciudad).
# 5) Fase 1 MILP 100% LINEAL (sin ceil en objetivo) -> CBC/LP compatible.
# 6) Simulación regiones:
#    - Opción A: si tv > H_DIA => día solo viaje, duerme en destino, trabaja al día siguiente.
#    - Si técnico tiene instalaciones en su base, puede instalar en base y luego viajar a otra ciudad el mismo día.
#
# Requiere: pandas, numpy, openpyxl, pyomo, pulp
# Solver: CBC vía PuLP
#
# Inputs en ./data/:
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
# Outputs en ./outputs/:
#   resultado_optimizacion_gps_fase1.xlsx
#   resultado_optimizacion_gps_plan_global.xlsx

import os
import math
from copy import deepcopy
from datetime import time as dt_time
from collections import Counter

import numpy as np
import pandas as pd
import pyomo.environ as pyo
import pulp

print("[INFO] RUNNING FILE:", __file__)

# =========================
# 0. CONFIG
# =========================
PATH = "data/"
OUTPUTS_DIR = "outputs"
SANTIAGO = "Santiago"

os.makedirs(OUTPUTS_DIR, exist_ok=True)

# Solver: CBC localizado vía PuLP
CBC_EXE = pulp.apis.PULP_CBC_CMD().path

# =========================
# 1. UTILIDADES
# =========================
def time_to_hours(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return 0.0
    if isinstance(x, dt_time):
        return x.hour + x.minute / 60.0 + x.second / 3600.0
    if isinstance(x, str) and ":" in x:
        parts = x.strip().split(":")
        if len(parts) >= 2:
            hh = float(parts[0])
            mm = float(parts[1])
            ss = float(parts[2]) if len(parts) >= 3 else 0.0
            return hh + mm / 60.0 + ss / 3600.0
    try:
        return float(x)
    except Exception:
        return 0.0

def safe_float(x, default=0.0):
    try:
        if x is None:
            return default
        if isinstance(x, float) and np.isnan(x):
            return default
        if isinstance(x, dt_time):
            return time_to_hours(x)
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

# =========================
# 2. CARGA DE DATOS (UF)
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
# 3. NORMALIZACIÓN + SETS
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
# 4. PARÁMETROS / DEMANDA
# =========================
param = param_df.set_index("parametro")["valor"].to_dict()

# Todo en UF
PRECIO_BENCINA_UF_KM = safe_float(param.get("precio_bencina"), 0.03)  # UF/km
ALOJ_UF = safe_float(param.get("alojamiento_uf_noche"), 1.1)
ALMU_UF = safe_float(param.get("almuerzo_uf_dia"), 0.5)
INCENTIVO_UF = safe_float(param.get("incentivo_por_gps"), 1.12)

H_DIA = safe_float(param.get("horas_jornada"), 7.0)         # horas totales del día (incluye viaje)
VEL = safe_float(param.get("velocidad_terrestre"), 80.0)    # km/h
TIEMPO_INST_GPS_H = safe_float(param.get("tiempo_instalacion_gps"), 0.75)

DIAS_SEM = int(safe_float(param.get("dias_semana"), 6))
SEMANAS = int(safe_float(param.get("semanas_proyecto"), 4))
DIAS_MAX = DIAS_SEM * SEMANAS

HH_MES = safe_float(param.get("hh_mes"), 180.0)

# Demanda
demanda["gps_total"] = demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]
demanda["horas"] = TIEMPO_INST_GPS_H * demanda["gps_total"]

H = dict(zip(demanda["ciudad"], demanda["horas"]))              # horas instalación requeridas por ciudad
GPS_TOTAL = dict(zip(demanda["ciudad"], demanda["gps_total"]))  # GPS totales por ciudad

# Materiales (UF por GPS)
KIT1_UF = safe_float(kits.loc[kits["tipo_kit"] == "1_GPS", "costo"].values[0], 0.0) if (kits["tipo_kit"] == "1_GPS").any() else 0.0
KIT2_UF = safe_float(kits.loc[kits["tipo_kit"] == "2_GPS", "costo"].values[0], 0.0) if (kits["tipo_kit"] == "2_GPS").any() else 0.0

demanda["mat_uf"] = demanda["vehiculos_1gps"] * KIT1_UF + demanda["vehiculos_2gps"] * KIT2_UF
MATERIAL_UF = dict(zip(demanda["ciudad"], demanda["mat_uf"]))

# Externos: PXQ UF por GPS
pxq["ciudad"] = pxq["ciudad"].apply(norm_city)
PXQ_UF_PER_GPS = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))  # UF/GPS

# Flete por ciudad (UF)
flete["ciudad"] = flete["ciudad"].apply(norm_city)
FLETE_UF = dict(zip(flete["ciudad"], flete["costo_flete"]))  # UF

# =========================
# 5. FUNCIONES BASE
# =========================
def base_tecnico(tecnico: str) -> str:
    return internos.loc[internos["tecnico"] == tecnico, "ciudad_base"].values[0]

def hh_semana(tecnico: str) -> float:
    return safe_float(internos.loc[internos["tecnico"] == tecnico, "hh_semana_proyecto"].values[0], 0.0)

def alpha_tecnico(tecnico: str) -> float:
    denom = max(1e-9, DIAS_SEM * H_DIA)
    return hh_semana(tecnico) / denom

def horas_diarias_instal(tecnico: str) -> float:
    # capacidad diaria efectiva de instalación
    return H_DIA * alpha_tecnico(tecnico)

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
        peaje_uf = safe_float(peajes.loc[ciudad_origen, ciudad_destino], 0.0)  # UF
        return dist_km * PRECIO_BENCINA_UF_KM + peaje_uf
    return safe_float(avion_cost.loc[ciudad_origen, ciudad_destino], 0.0)  # UF

def costo_sueldo_proyecto_uf(tecnico: str) -> float:
    sueldo_mes = safe_float(internos.loc[internos["tecnico"] == tecnico, "sueldo_uf"].values[0], 0.0)
    hh_proy = hh_semana(tecnico) * SEMANAS
    return sueldo_mes * (hh_proy / max(1e-9, HH_MES))

def costo_externo_ciudad_uf(ciudad: str) -> float:
    # PXQ por GPS + flete por ciudad + materiales por ciudad
    pxq_uf = safe_float(PXQ_UF_PER_GPS.get(ciudad, 0.0), 0.0) * safe_float(GPS_TOTAL.get(ciudad, 0.0), 0.0)
    flete_uf = safe_float(FLETE_UF.get(ciudad, 0.0), 0.0)
    mat_uf = safe_float(MATERIAL_UF.get(ciudad, 0.0), 0.0)
    return pxq_uf + flete_uf + mat_uf

def dias_ciudad_aprox(ciudad: str, tecnico: str, modo: str, origen: str) -> int:
    # aproximación para MILP
    tv = t_viaje(origen, ciudad, modo)
    hd_inst = horas_diarias_instal(tecnico)

    time_for_work = max(0.0, H_DIA - tv)
    inst_cap_day1 = min(hd_inst, time_for_work)
    rem = max(0.0, H[ciudad] - inst_cap_day1)

    if rem <= 1e-9:
        return 1
    return 1 + int(math.ceil(rem / max(1e-9, hd_inst)))

def costo_interno_aprox_ciudad_uf(ciudad: str, tecnico: str, modo: str) -> float:
    """
    costo aproximado para MILP para ciudad completa interna (no Santiago):
    sueldo + almuerzo + alojamiento (si fuera base) + incentivo por GPS + viaje base->ciudad + flete + materiales
    """
    base = base_tecnico(tecnico)
    dias = dias_ciudad_aprox(ciudad, tecnico, modo, origen=base)

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1e-9, DIAS_MAX)

    costo = 0.0
    costo += dias * sueldo_dia
    costo += dias * ALMU_UF

    if ciudad != base:
        costo += dias * ALOJ_UF

    costo += INCENTIVO_UF * safe_float(GPS_TOTAL.get(ciudad, 0.0), 0.0)
    costo += costo_viaje_uf(base, ciudad, modo)

    # flete aplica salvo caso base=Santiago y llega terrestre
    flete_aplica = (base != SANTIAGO) or (modo == "avion")
    if flete_aplica:
        costo += safe_float(FLETE_UF.get(ciudad, 0.0), 0.0)

    costo += safe_float(MATERIAL_UF.get(ciudad, 0.0), 0.0)

    return costo

# =========================
# 6. FASE 1 – MILP (LINEAL, Santiago mixto)
# =========================
def solve_phase1():
    """
    MILP lineal:
      - Para ciudades != Santiago: interno (1 técnico+modo) o externo.
      - Santiago: mixto con z[t] (GPS internos por técnico) y gs_ext (GPS externos).
      - LINEALIZACIÓN días_scl[t]:
            TIEMPO_INST_GPS_H * z[t] <= hd_inst[t] * dias_scl[t]
        (sin ceil, CBC compatible)
    """
    m = pyo.ConcreteModel()

    m.C = pyo.Set(initialize=CIUDADES)
    m.T = pyo.Set(initialize=TECNICOS)
    m.M = pyo.Set(initialize=MODOS)

    # Regiones
    m.x = pyo.Var(m.C, m.T, m.M, domain=pyo.Binary)
    m.y = pyo.Var(m.C, domain=pyo.Binary)

    # Santiago mixto
    gps_scl = int(round(safe_float(GPS_TOTAL.get(SANTIAGO, 0.0), 0.0)))
    m.z = pyo.Var(m.T, domain=pyo.NonNegativeIntegers, bounds=(0, gps_scl))
    m.gs_ext = pyo.Var(domain=pyo.NonNegativeIntegers, bounds=(0, gps_scl))
    m.dias_scl = pyo.Var(m.T, domain=pyo.NonNegativeIntegers, bounds=(0, DIAS_MAX))

    # Constantes Santiago
    mat_scl_total = safe_float(MATERIAL_UF.get(SANTIAGO, 0.0), 0.0)
    pxq_scl_per = safe_float(PXQ_UF_PER_GPS.get(SANTIAGO, 0.0), 0.0)
    flete_scl = safe_float(FLETE_UF.get(SANTIAGO, 0.0), 0.0)  # input ya debería venir 0

    def obj_rule(mm):
        cost = 0.0

        # Regiones
        for c in mm.C:
            if c == SANTIAGO:
                continue
            cost += sum(
                mm.x[c, t, mo] * costo_interno_aprox_ciudad_uf(c, t, mo)
                for t in mm.T for mo in mm.M
            )
            cost += (1 - mm.y[c]) * costo_externo_ciudad_uf(c)

        # Santiago interno
        for t in mm.T:
            zt = mm.z[t]

            sueldo_proy = costo_sueldo_proyecto_uf(t)
            sueldo_dia = sueldo_proy / max(1e-9, DIAS_MAX)

            cost += mm.dias_scl[t] * (sueldo_dia + ALMU_UF)
            cost += INCENTIVO_UF * zt

            if gps_scl > 0:
                cost += mat_scl_total * (zt / gps_scl)

        # Santiago externo
        cost += pxq_scl_per * mm.gs_ext
        cost += flete_scl
        if gps_scl > 0:
            cost += mat_scl_total * (mm.gs_ext / gps_scl)

        return cost

    m.OBJ = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

    # Regiones linking
    def link_xy(mm, c, t, mo):
        if c == SANTIAGO:
            return pyo.Constraint.Skip
        return mm.x[c, t, mo] <= mm.y[c]
    m.LINK = pyo.Constraint(m.C, m.T, m.M, rule=link_xy)

    def unica_ciudad(mm, c):
        if c == SANTIAGO:
            return pyo.Constraint.Skip
        return sum(mm.x[c, t, mo] for t in mm.T for mo in mm.M) == mm.y[c]
    m.UNICA = pyo.Constraint(m.C, rule=unica_ciudad)

    def cap_tecnico(mm, t):
        base = base_tecnico(t)
        return sum(
            dias_ciudad_aprox(c, t, mo, origen=base) * mm.x[c, t, mo]
            for c in mm.C if c != SANTIAGO for mo in mm.M
        ) <= DIAS_MAX
    m.CAP = pyo.Constraint(m.T, rule=cap_tecnico)

    # Santiago balance
    def scl_balance(mm):
        return sum(mm.z[t] for t in mm.T) + mm.gs_ext == gps_scl
    m.SCL = pyo.Constraint(rule=scl_balance)

    # Santiago capacidad total técnico en proyecto
    def scl_cap_total(mm, t):
        hd = max(1e-9, horas_diarias_instal(t))
        hmax = DIAS_MAX * hd
        return mm.z[t] * TIEMPO_INST_GPS_H <= hmax
    m.SCL_CAP_TOT = pyo.Constraint(m.T, rule=scl_cap_total)

    # Santiago días lineales
    def scl_days_link(mm, t):
        hd = max(1e-9, horas_diarias_instal(t))
        return mm.z[t] * TIEMPO_INST_GPS_H <= hd * mm.dias_scl[t]
    m.SCL_DIAS_LINK = pyo.Constraint(m.T, rule=scl_days_link)

    # Solve
    if not CBC_EXE or not os.path.exists(CBC_EXE):
        raise RuntimeError("No se encontró CBC vía PuLP. Reinstala pulp o revisa PULP_CBC_CMD().path")
    solver = pyo.SolverFactory("cbc", executable=CBC_EXE)
    solver.solve(m)

    # Export fase 1
    rows = []

    for c in CIUDADES:
        if c == SANTIAGO:
            continue
        for t in TECNICOS:
            for mo in MODOS:
                if pyo.value(m.x[c, t, mo]) > 0.5:
                    rows.append([
                        c, t, mo,
                        float(costo_interno_aprox_ciudad_uf(c, t, mo)),
                        int(dias_ciudad_aprox(c, t, mo, origen=base_tecnico(t))),
                        "CIUDAD_COMPLETA_INTERNA"
                    ])

    z_scl = {}
    for t in TECNICOS:
        zt = int(round(pyo.value(m.z[t])))
        z_scl[t] = zt
        if zt > 0:
            rows.append([SANTIAGO, t, "base", np.nan, int(round(pyo.value(m.dias_scl[t]))), f"SCL_GPS_INTERNOS={zt}"])

    gs_ext_val = int(round(pyo.value(m.gs_ext)))
    if gs_ext_val > 0:
        rows.append([SANTIAGO, "EXTERNO", "pxq", np.nan, np.nan, f"SCL_GPS_EXTERNOS={gs_ext_val}"])

    df = pd.DataFrame(rows, columns=["ciudad", "tecnico", "modo", "costo_aprox_uf", "dias_aprox", "nota"])
    df.to_excel(os.path.join(OUTPUTS_DIR, "resultado_optimizacion_gps_fase1.xlsx"), index=False)

    # ws
    y_val = {c: int(pyo.value(m.y[c]) > 0.5) for c in CIUDADES if c != SANTIAGO}

    assign = {}
    mode = {}
    for c in CIUDADES:
        if c == SANTIAGO:
            continue
        for t in TECNICOS:
            for mo in MODOS:
                if pyo.value(m.x[c, t, mo]) > 0.5:
                    assign[(t, c)] = 1
                    mode[(t, c)] = mo

    return {"I": y_val, "assign": assign, "mode": mode, "z_scl": z_scl, "gs_ext": gs_ext_val}

# =========================
# 7. FASE 2 – SIMULACIÓN REGIONES + MEJORA
# =========================
def build_initial_solution(ws):
    city_type = {}
    for c in CIUDADES:
        if c == SANTIAGO:
            city_type[c] = "mixto_scl"
        else:
            city_type[c] = "interno" if ws["I"].get(c, 0) == 1 else "externo"

    tech_cities = {t: [] for t in TECNICOS}
    for (t, c), _ in ws["assign"].items():
        if c != SANTIAGO:
            tech_cities[t].append(c)

    scl_internos = ws.get("z_scl", {})
    gs_ext = ws.get("gs_ext", 0)

    return city_type, tech_cities, scl_internos, gs_ext

def simulate_tech_schedule_regiones(tecnico, cities_list):
    """
    Simula ciudades fuera de Santiago para un técnico.
    FIX:
      - Opción A: si tv > H_DIA => día solo viaje.
      - Si arranca en base y tiene demanda en base, puede instalar en base y luego viajar el mismo día.
    """
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

    pending_h = {c: H[c] for c in cities_list if c in H}
    added_material = set()

    def flete_aplica(ciudad, modo_llegada):
        if base != SANTIAGO:
            return True
        return modo_llegada == "avion"

    for c in cities_list:
        if c not in pending_h:
            continue
        if day > DIAS_MAX:
            break

        if c not in added_material:
            cost["material_uf"] += safe_float(MATERIAL_UF.get(c, 0.0), 0.0)
            added_material.add(c)

        if pending_h.get(c, 0.0) <= 1e-9:
            continue

        road_cost = costo_viaje_uf(sleep_city, c, "terrestre")
        air_cost = costo_viaje_uf(sleep_city, c, "avion")
        modo_in = "avion" if air_cost < road_cost else "terrestre"

        tv = t_viaje(sleep_city, c, modo_in)
        cv = costo_viaje_uf(sleep_city, c, modo_in)

        # Opción A: día solo viaje
        if sleep_city != c and tv > H_DIA + 1e-9:
            cost["travel_uf"] += cv
            cost["alm_uf"] += ALMU_UF
            cost["sueldo_uf"] += sueldo_dia

            flete_day = safe_float(FLETE_UF.get(c, 0.0), 0.0) if flete_aplica(c, modo_in) else 0.0
            cost["flete_uf"] += flete_day

            sleep_city = c
            aloj_day = ALOJ_UF if sleep_city != base else 0.0
            cost["aloj_uf"] += aloj_day

            plan.append({
                "tecnico": tecnico, "dia": day,
                "ciudad_trabajo": c,
                "horas_instal": 0.0, "gps_inst": 0.0,
                "viaje_modo_manana": modo_in, "viaje_h_manana": tv,
                "duerme_en": sleep_city,
                "viaje_uf": cv, "aloj_uf": aloj_day, "alm_uf": ALMU_UF,
                "sueldo_uf": sueldo_dia, "inc_uf": 0.0,
                "flete_uf": flete_day, "material_uf": 0.0,
                "nota": "DIA_SOLO_VIAJE (tv>H_DIA)"
            })
            day += 1
            continue

        # FIX BASE: instala en base y viaja
        if sleep_city == base and c != base:
            time_for_install_before_travel = max(0.0, H_DIA - tv)
            inst_cap_today = min(hd_inst, time_for_install_before_travel)

            installed_base = 0.0
            gps_inst_base = 0.0
            inc_base = 0.0

            if base in pending_h and pending_h[base] > 1e-9 and inst_cap_today > 1e-9:
                installed_base = min(pending_h[base], inst_cap_today)
                pending_h[base] -= installed_base
                gps_inst_base = installed_base / max(1e-9, TIEMPO_INST_GPS_H)
                inc_base = INCENTIVO_UF * gps_inst_base
                cost["inc_uf"] += inc_base

                if base not in added_material:
                    cost["material_uf"] += safe_float(MATERIAL_UF.get(base, 0.0), 0.0)
                    added_material.add(base)

            cost["travel_uf"] += cv
            cost["alm_uf"] += ALMU_UF
            cost["sueldo_uf"] += sueldo_dia

            flete_day = safe_float(FLETE_UF.get(c, 0.0), 0.0) if flete_aplica(c, modo_in) else 0.0
            cost["flete_uf"] += flete_day

            sleep_city = c
            aloj_day = ALOJ_UF if sleep_city != base else 0.0
            cost["aloj_uf"] += aloj_day

            plan.append({
                "tecnico": tecnico, "dia": day,
                "ciudad_trabajo": base,
                "horas_instal": installed_base, "gps_inst": gps_inst_base,
                "viaje_modo_manana": f"TRAVEL_AFTER_BASE_WORK->{modo_in}",
                "viaje_h_manana": tv,
                "duerme_en": sleep_city,
                "viaje_uf": cv, "aloj_uf": aloj_day, "alm_uf": ALMU_UF,
                "sueldo_uf": sueldo_dia, "inc_uf": inc_base,
                "flete_uf": flete_day, "material_uf": 0.0,
                "nota": "INSTALA_BASE_Y_VIAJA"
            })
            day += 1

        else:
            # normal: viaja y trabaja en destino el mismo día
            cost["travel_uf"] += cv
            cost["alm_uf"] += ALMU_UF
            cost["sueldo_uf"] += sueldo_dia

            flete_day = safe_float(FLETE_UF.get(c, 0.0), 0.0) if flete_aplica(c, modo_in) else 0.0
            cost["flete_uf"] += flete_day

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
                "tecnico": tecnico, "dia": day,
                "ciudad_trabajo": c,
                "horas_instal": installed, "gps_inst": gps_inst,
                "viaje_modo_manana": modo_in, "viaje_h_manana": tv,
                "duerme_en": sleep_city,
                "viaje_uf": cv, "aloj_uf": aloj_day, "alm_uf": ALMU_UF,
                "sueldo_uf": sueldo_dia, "inc_uf": inc_day,
                "flete_uf": flete_day, "material_uf": 0.0,
                "nota": ""
            })
            day += 1

        # continúa en la ciudad objetivo (c) hasta terminar
        while pending_h.get(c, 0.0) > 1e-9 and day <= DIAS_MAX:
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
                "tecnico": tecnico, "dia": day,
                "ciudad_trabajo": c,
                "horas_instal": installed, "gps_inst": gps_inst,
                "viaje_modo_manana": None, "viaje_h_manana": 0.0,
                "duerme_en": sleep_city,
                "viaje_uf": 0.0, "aloj_uf": aloj_day, "alm_uf": ALMU_UF,
                "sueldo_uf": sueldo_dia, "inc_uf": inc_day,
                "flete_uf": 0.0, "material_uf": 0.0,
                "nota": ""
            })
            day += 1

    complete = all(hh <= 1e-6 for hh in pending_h.values())
    feasible = (day - 1) <= DIAS_MAX and complete
    last_day = day - 1
    return plan, cost, feasible, last_day, pending_h

def cost_santiago_mix(scl_internos_by_t, gs_ext):
    gps_scl = int(round(safe_float(GPS_TOTAL.get(SANTIAGO, 0.0), 0.0)))
    mat_total = safe_float(MATERIAL_UF.get(SANTIAGO, 0.0), 0.0)
    flete = safe_float(FLETE_UF.get(SANTIAGO, 0.0), 0.0)
    pxq_per = safe_float(PXQ_UF_PER_GPS.get(SANTIAGO, 0.0), 0.0)

    rows = []
    total = 0.0

    # internos
    for t, z in scl_internos_by_t.items():
        z = int(z)
        if z <= 0:
            continue

        hd = max(1e-9, horas_diarias_instal(t))
        horas = z * TIEMPO_INST_GPS_H
        dias = int(math.ceil(horas / hd))

        sueldo_proy = costo_sueldo_proyecto_uf(t)
        sueldo_dia = sueldo_proy / max(1e-9, DIAS_MAX)

        c_sueldo = dias * sueldo_dia
        c_alm = dias * ALMU_UF
        c_inc = z * INCENTIVO_UF
        c_mat = (mat_total * (z / gps_scl)) if gps_scl > 0 else 0.0

        c_tot = c_sueldo + c_alm + c_inc + c_mat
        total += c_tot

        rows.append({
            "responsable": t, "tipo": "SCL_INTERNO",
            "gps": z, "dias": dias,
            "travel_uf": 0.0, "aloj_uf": 0.0,
            "alm_uf": c_alm, "inc_uf": c_inc,
            "sueldo_uf": c_sueldo, "flete_uf": 0.0,
            "material_uf": c_mat, "pxq_uf": 0.0,
            "total_uf": c_tot
        })

    # externo
    gs_ext = int(gs_ext)
    if gs_ext > 0:
        c_pxq = pxq_per * gs_ext
        c_mat = (mat_total * (gs_ext / gps_scl)) if gps_scl > 0 else 0.0
        c_tot = c_pxq + flete + c_mat
        total += c_tot

        rows.append({
            "responsable": "Santiago", "tipo": "SCL_EXTERNO",
            "gps": gs_ext, "dias": 0,
            "travel_uf": 0.0, "aloj_uf": 0.0,
            "alm_uf": 0.0, "inc_uf": 0.0,
            "sueldo_uf": 0.0, "flete_uf": flete,
            "material_uf": c_mat, "pxq_uf": c_pxq,
            "total_uf": c_tot
        })

    return rows, total

def total_cost_solution(city_type, tech_cities, scl_internos_by_t, gs_ext):
    total = 0.0

    # internos regiones
    for t, clist in tech_cities.items():
        if not clist:
            continue
        _, cst, feas, _, _ = simulate_tech_schedule_regiones(t, clist)
        if not feas:
            return 1e18
        total += sum(cst.values())

    # externos regiones
    for c in CIUDADES:
        if c == SANTIAGO:
            continue
        if city_type.get(c) == "externo":
            total += costo_externo_ciudad_uf(c)

    # Santiago mixto
    _, scl_total = cost_santiago_mix(scl_internos_by_t, gs_ext)
    total += scl_total

    return total

def improve_solution(city_type, tech_cities, scl_internos_by_t, gs_ext, iters=400, seed=42):
    best_ct = deepcopy(city_type)
    best_tc = deepcopy(tech_cities)
    best_scl = deepcopy(scl_internos_by_t)
    best_gs = int(gs_ext)

    best_cost = total_cost_solution(best_ct, best_tc, best_scl, best_gs)

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
                best_cost_t = 1e18

                for t in TECNICOS:
                    if c in tc2[t]:
                        continue
                    trial = tc2[t] + [c]
                    _, cst, feas, _, _ = simulate_tech_schedule_regiones(t, trial)
                    if not feas:
                        continue
                    cost_t = sum(cst.values())
                    if cost_t < best_cost_t:
                        best_cost_t = cost_t
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

        new_cost = total_cost_solution(ct2, tc2, best_scl, best_gs)
        if new_cost + 1e-6 < best_cost:
            best_cost = new_cost
            best_ct = ct2
            best_tc = tc2

    return best_ct, best_tc, best_scl, best_gs, best_cost

# =========================
# 8. RUN + EXPORT
# =========================
def run_all():
    print(f"[INFO] CBC_EXE = {CBC_EXE}")

    ws = solve_phase1()
    city_type, tech_cities, scl_internos_by_t, gs_ext = build_initial_solution(ws)

    # asegurar que si la base del técnico tiene demanda, la incluimos en su lista (para permitir instalar en base)
    for t in TECNICOS:
        b = base_tecnico(t)
        if b in CIUDADES and safe_float(H.get(b, 0.0), 0.0) > 1e-9:
            if b not in tech_cities[t]:
                tech_cities[t] = [b] + tech_cities[t]

    city_type2, tech_cities2, scl2, gs2, best_cost = improve_solution(
        city_type, tech_cities, scl_internos_by_t, gs_ext, iters=400
    )

    # Validación: internas regiones asignadas
    internas = [c for c in CIUDADES if c != SANTIAGO and city_type2.get(c) == "interno"]
    asignadas = set()
    for t, clist in tech_cities2.items():
        for c in clist:
            if c != SANTIAGO:
                asignadas.add(c)

    faltantes = [c for c in internas if c not in asignadas]
    if faltantes:
        raise RuntimeError("Plan inconsistente: ciudades INTERNAS sin técnico asignado: " + ", ".join(faltantes))

    # Validación: no más de 1 técnico por ciudad (regiones)
    cnt = Counter()
    for t, clist in tech_cities2.items():
        for c in clist:
            if c != SANTIAGO:
                cnt[c] += 1
    duplicadas = [c for c, k in cnt.items() if k > 1]
    if duplicadas:
        raise RuntimeError("Regla violada: más de un técnico asignado a ciudad (regiones): " + ", ".join(duplicadas))

    plan_rows = []
    cost_rows = []
    city_rows = []

    # internos regiones
    for t, clist in tech_cities2.items():
        if not clist:
            continue
        plan, cst, feas, last_day, pending = simulate_tech_schedule_regiones(t, clist)
        if not feas:
            raise RuntimeError(f"Solución infeasible en regiones para técnico {t} (last_day={last_day})")

        plan_rows.extend(plan)
        cost_rows.append({
            "responsable": t,
            "tipo": "INTERNO_REGIONES",
            **cst,
            "pxq_uf": 0.0,
            "total_uf": sum(cst.values())
        })

    # externos regiones
    for c in CIUDADES:
        if c == SANTIAGO:
            continue
        if city_type2.get(c) == "externo":
            pxq_total = safe_float(PXQ_UF_PER_GPS.get(c, 0.0), 0.0) * safe_float(GPS_TOTAL.get(c, 0.0), 0.0)
            cost_rows.append({
                "responsable": c,
                "tipo": "EXTERNO_REGIONES",
                "travel_uf": 0.0,
                "aloj_uf": 0.0,
                "alm_uf": 0.0,
                "inc_uf": 0.0,
                "sueldo_uf": 0.0,
                "flete_uf": safe_float(FLETE_UF.get(c, 0.0), 0.0),
                "material_uf": safe_float(MATERIAL_UF.get(c, 0.0), 0.0),
                "pxq_uf": pxq_total,
                "total_uf": costo_externo_ciudad_uf(c),
            })

            city_rows.append({
                "ciudad": c,
                "tipo_final": "externo",
                "gps_total": safe_float(GPS_TOTAL.get(c, 0.0), 0.0),
                "gps_int": 0.0,
                "gps_ext": safe_float(GPS_TOTAL.get(c, 0.0), 0.0),
                "material_uf": safe_float(MATERIAL_UF.get(c, 0.0), 0.0),
                "flete_uf": safe_float(FLETE_UF.get(c, 0.0), 0.0),
                "pxq_uf": pxq_total,
                "total_uf": costo_externo_ciudad_uf(c),
            })
        else:
            city_rows.append({
                "ciudad": c,
                "tipo_final": "interno",
                "gps_total": safe_float(GPS_TOTAL.get(c, 0.0), 0.0),
                "gps_int": safe_float(GPS_TOTAL.get(c, 0.0), 0.0),
                "gps_ext": 0.0,
                "material_uf": safe_float(MATERIAL_UF.get(c, 0.0), 0.0),
                "flete_uf": safe_float(FLETE_UF.get(c, 0.0), 0.0),
                "pxq_uf": 0.0,
                "total_uf": np.nan,
            })

    # Santiago mixto
    scl_cost_rows, scl_total = cost_santiago_mix(scl2, gs2)
    cost_rows.extend(scl_cost_rows)

    gps_scl = safe_float(GPS_TOTAL.get(SANTIAGO, 0.0), 0.0)
    gps_int_scl = sum(int(v) for v in scl2.values())
    gps_ext_scl = int(gs2)

    city_rows.append({
        "ciudad": SANTIAGO,
        "tipo_final": "mixto_scl",
        "gps_total": gps_scl,
        "gps_int": gps_int_scl,
        "gps_ext": gps_ext_scl,
        "material_uf": safe_float(MATERIAL_UF.get(SANTIAGO, 0.0), 0.0),
        "flete_uf": safe_float(FLETE_UF.get(SANTIAGO, 0.0), 0.0),
        "pxq_uf": safe_float(PXQ_UF_PER_GPS.get(SANTIAGO, 0.0), 0.0) * gps_ext_scl,
        "total_uf": scl_total
    })

    df_plan = pd.DataFrame(plan_rows)
    if df_plan.empty:
        df_plan = pd.DataFrame(columns=[
            "tecnico", "dia", "ciudad_trabajo", "horas_instal", "gps_inst",
            "viaje_modo_manana", "viaje_h_manana", "duerme_en",
            "viaje_uf", "aloj_uf", "alm_uf", "sueldo_uf", "inc_uf",
            "flete_uf", "material_uf", "nota"
        ])
    else:
        df_plan = df_plan.sort_values(["tecnico", "dia"])

    df_cost = pd.DataFrame(cost_rows)
    if df_cost.empty:
        df_cost = pd.DataFrame(columns=[
            "responsable","tipo","travel_uf","aloj_uf","alm_uf","inc_uf","sueldo_uf","flete_uf","material_uf","pxq_uf","total_uf"
        ])
    else:
        df_cost = df_cost.sort_values(["tipo", "total_uf"], ascending=[True, False])

    df_city = pd.DataFrame(city_rows).sort_values(["tipo_final", "ciudad"])

    total_final = float(df_cost["total_uf"].sum()) if not df_cost.empty else 0.0
    baseline_externo = float(sum(costo_externo_ciudad_uf(c) for c in CIUDADES))
    ahorro = baseline_externo - total_final

    df_resumen = pd.DataFrame([{
        "total_final_uf": total_final,
        "baseline_todo_externo_uf": baseline_externo,
        "ahorro_vs_externo_uf": ahorro,
        "ciudades_total": len(CIUDADES),
        "dias_max": DIAS_MAX,
        "nota": "Inputs 100% UF | PXQ por GPS | Materiales incluidos | Santiago mixto | Opción A tv>H_DIA | Base instala+viaja"
    }])

    out_path = os.path.join(OUTPUTS_DIR, "resultado_optimizacion_gps_plan_global.xlsx")
    with pd.ExcelWriter(out_path) as w:
        df_resumen.to_excel(w, index=False, sheet_name="Resumen_Total")
        df_city.to_excel(w, index=False, sheet_name="Costos_por_Ciudad")
        df_plan.to_excel(w, index=False, sheet_name="Plan_Diario")
        df_cost.to_excel(w, index=False, sheet_name="Costos_Detalle")

    print("[OK] ->", out_path)
    print("[OK] Costo total (UF):", round(total_final, 4))
    print("[OK] Baseline todo externo (UF):", round(baseline_externo, 4))
    print("[OK] Ahorro vs externo (UF):", round(ahorro, 4))

if __name__ == "__main__":
    run_all()
