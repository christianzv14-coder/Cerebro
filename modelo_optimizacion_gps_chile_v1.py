# modelo_optimizacion_gps_chile_FINAL.py
# Optimización costos instalación GPS (Chile) – FINAL CORREGIDO
#
# FIXES incluidos:
# 1) hh_semana_proyecto viene en DÍAS/SEMANA (no horas/semana)  ✅
# 2) Inputs están en UF (NO dividir por UF) ✅
# 3) PXQ es UF POR GPS (se multiplica por GPS externos) ✅
# 4) Santiago MIXTO real: internos en base instalan parte; remanente queda externo ✅
# 5) Opción A viaje: si tv > hh_día => ese día SOLO viaja, duerme destino, instala al siguiente ✅
# 6) GPS instalados DISCRETOS (enteros): se acabó el "0.7 gps" ✅
# 7) Materiales incluidos SIEMPRE (una sola vez por ciudad, no duplicar) ✅
#
# Requiere: pandas, numpy, openpyxl, pyomo, pulp (CBC)
# Inputs en ./data/
# Outputs en ./outputs/plan_global_operativo.xlsx

import os
import math
from copy import deepcopy
from datetime import time as dt_time
from collections import Counter, defaultdict

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
# 2) CARGA DE DATOS (UF)
# =========================
demanda = pd.read_excel(os.path.join(PATH, "demanda_ciudades.xlsx"))
internos = pd.read_excel(os.path.join(PATH, "tecnicos_internos.xlsx"))
pxq = pd.read_excel(os.path.join(PATH, "costos_externos.xlsx"))
flete = pd.read_excel(os.path.join(PATH, "flete_ciudad.xlsx"))
kits = pd.read_excel(os.path.join(PATH, "materiales.xlsx"))
param_df = pd.read_excel(os.path.join(PATH, "parametros.xlsx"))

km = pd.read_excel(os.path.join(PATH, "matriz_distancia_km.xlsx"), index_col=0)
peajes = pd.read_excel(os.path.join(PATH, "matriz_peajes.xlsx"), index_col=0)          # UF
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

# Operación
H_DIA = safe_float(param.get("horas_jornada"), 7.0)
VEL = safe_float(param.get("velocidad_terrestre"), 80.0)
TIEMPO_INST_GPS_H = safe_float(param.get("tiempo_instalacion_gps"), 1.25)

DIAS_SEM = int(safe_float(param.get("dias_semana"), 6))
SEMANAS = int(safe_float(param.get("semanas_proyecto"), 4))
DIAS_MAX = DIAS_SEM * SEMANAS
HH_MES = safe_float(param.get("hh_mes"), 180.0)

# Costos UF
ALOJ_UF = safe_float(param.get("alojamiento_uf_noche"), 1.1)
ALMU_UF = safe_float(param.get("almuerzo_uf_dia"), 0.5)
INCENTIVO_UF = safe_float(param.get("incentivo_por_gps"), 1.12)

# Si quieres costo variable por km (UF/km), lo puedes tener como parámetro.
# Si no está, se asume 0 y el terrestre queda con peajes solamente (UF) + lo que tu negocio ya embeba en otros conceptos.
PRECIO_BENCINA_UF_KM = safe_float(param.get("precio_bencina_uf_km"), 0.0)

demanda["vehiculos_1gps"] = demanda["vehiculos_1gps"].fillna(0).astype(float)
demanda["vehiculos_2gps"] = demanda["vehiculos_2gps"].fillna(0).astype(float)

demanda["gps_total"] = demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]
demanda["gps_total"] = demanda["gps_total"].round().astype(int)

GPS_TOTAL = dict(zip(demanda["ciudad"], demanda["gps_total"]))
V1 = dict(zip(demanda["ciudad"], demanda["vehiculos_1gps"]))
V2 = dict(zip(demanda["ciudad"], demanda["vehiculos_2gps"]))

# Kits (UF)
kits["tipo_kit"] = kits["tipo_kit"].astype(str)
KIT1_UF = safe_float(kits.loc[kits["tipo_kit"] == "1_GPS", "costo"].values[0], 0.0)
KIT2_UF = safe_float(kits.loc[kits["tipo_kit"] == "2_GPS", "costo"].values[0], 0.0)

def costo_materiales_ciudad(ciudad: str) -> float:
    return KIT1_UF * safe_float(V1.get(ciudad, 0.0), 0.0) + KIT2_UF * safe_float(V2.get(ciudad, 0.0), 0.0)

# PXQ y flete (UF)
pxq["ciudad"] = pxq["ciudad"].apply(norm_city)
flete["ciudad"] = flete["ciudad"].apply(norm_city)

# PXQ externo en UF POR GPS
PXQ_UF_POR_GPS = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))

# Flete en UF por ciudad (ya viene UF; NO dividir)
FLETE_UF = dict(zip(flete["ciudad"], flete["costo_flete"]))

# =========================
# 5) FUNCIONES BASE
# =========================
def base_tecnico(tecnico: str) -> str:
    return internos.loc[internos["tecnico"] == tecnico, "ciudad_base"].values[0]

def dias_semana_proyecto(tecnico: str) -> float:
    # FIX: este campo viene en DÍAS/SEMANA
    return safe_float(internos.loc[internos["tecnico"] == tecnico, "hh_semana_proyecto"].values[0], 0.0)

def horas_semana_proyecto(tecnico: str) -> float:
    # DÍAS/SEMANA * HORAS/DÍA
    return dias_semana_proyecto(tecnico) * H_DIA

def horas_diarias(tecnico: str) -> float:
    return horas_semana_proyecto(tecnico) / max(1e-9, DIAS_SEM)

def horas_totales_disponibles(tecnico: str) -> float:
    return horas_diarias(tecnico) * DIAS_MAX

def capacidad_gps_tecnico(tecnico: str) -> int:
    # capacidad total en GPS enteros
    return int(math.floor(horas_totales_disponibles(tecnico) / max(1e-9, TIEMPO_INST_GPS_H)))

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

def flete_aplica(ciudad: str, base: str, modo_llegada: str) -> bool:
    # Regla histórica: solo NO aplica si base Santiago y llega terrestre.
    # Tú ya dejaste flete Santiago = 0, así que queda consistente igual.
    if base == SANTIAGO and modo_llegada == "terrestre":
        return False
    return True

def costo_sueldo_proyecto_uf(tecnico: str) -> float:
    sueldo_mes = safe_float(internos.loc[internos["tecnico"] == tecnico, "sueldo_uf"].values[0], 0.0)
    hh_proy = horas_semana_proyecto(tecnico) * SEMANAS
    return sueldo_mes * (hh_proy / max(1e-9, HH_MES))

def costo_externo_uf(ciudad: str, gps_externos: int, base_ref: str = SANTIAGO, modo_ref: str = "terrestre") -> dict:
    """
    Externo: PXQ por GPS + flete si aplica (cuando gps_externos>0).
    Materiales se contabilizan aparte, una sola vez por ciudad (siempre).
    """
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

# =========================
# 6) FASE 1 – MILP (Regiones: interno vs externo)
# =========================
def solve_phase1():
    # Regiones = todas excepto Santiago
    C_REG = [c for c in CIUDADES if c != SANTIAGO]

    if not CBC_EXE or not os.path.exists(CBC_EXE):
        raise RuntimeError("No se encontró CBC vía PuLP. Reinstala pulp o revisa PULP_CBC_CMD().path")

    # Precomputos lineales para el MILP (aprox, sin secuencia)
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
        # si gps==0, dejamos 0 días (no debería pasar)
        return travel_day + max(1, install_days) if gps > 0 else 0

    def costo_interno_aprox_uf(tecnico: str, ciudad: str, modo: str) -> float:
        base = base_tecnico(tecnico)
        dias = dias_total_aprox(tecnico, ciudad, modo)
        if dias >= 10**8:
            return 1e15

        # viaje (una vez)
        viaje = costo_viaje_uf(base, ciudad, modo)

        # sueldo prorateado por días del proyecto
        sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
        sueldo_dia = sueldo_proy / max(1, DIAS_MAX)
        sue = sueldo_dia * dias

        # almuerzo por día
        alm = ALMU_UF * dias

        # alojamiento si fuera de base (por día/noche)
        alo = ALOJ_UF * dias if ciudad != base else 0.0

        # incentivo por GPS instalados (enteros)
        inc = INCENTIVO_UF * int(max(0, GPS_TOTAL.get(ciudad, 0)))

        # flete si aplica (una vez por ciudad)
        fle = safe_float(FLETE_UF.get(ciudad, 0.0), 0.0) if flete_aplica(ciudad, base, modo) else 0.0

        return viaje + sue + alm + alo + inc + fle

    def dias_consumidos_aprox(tecnico: str, ciudad: str, modo: str) -> int:
        return dias_total_aprox(tecnico, ciudad, modo)

    # Modelo
    m = pyo.ConcreteModel()
    m.C = pyo.Set(initialize=C_REG)
    m.T = pyo.Set(initialize=TECNICOS)
    m.M = pyo.Set(initialize=MODOS)

    # x[c,t,mo]=1 si ciudad c (región) la hace interno t por modo mo
    m.x = pyo.Var(m.C, m.T, m.M, domain=pyo.Binary)
    # y[c]=1 si ciudad c se hace interna, 0 si externa
    m.y = pyo.Var(m.C, domain=pyo.Binary)

    # objetivo lineal (sin materiales: los materiales van fijos aparte)
    def obj_rule(mm):
        cost = 0.0
        for c in mm.C:
            cost += sum(mm.x[c, t, mo] * costo_interno_aprox_uf(t, c, mo) for t in mm.T for mo in mm.M)

            # externo: pxq por GPS + flete (una vez)
            ext = costo_externo_uf(c, gps_externos=int(max(0, GPS_TOTAL.get(c, 0))))
            cost += (1 - mm.y[c]) * ext["total_externo_sin_materiales_uf"]
        return cost

    m.OBJ = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

    # linking
    def link_xy(mm, c, t, mo):
        return mm.x[c, t, mo] <= mm.y[c]
    m.LINK = pyo.Constraint(m.C, m.T, m.M, rule=link_xy)

    # si y=1 => exactamente una asignación (t,mo)
    def unica(mm, c):
        return sum(mm.x[c, t, mo] for t in mm.T for mo in mm.M) == mm.y[c]
    m.UNICA = pyo.Constraint(m.C, rule=unica)

    # capacidad por técnico (días máximos)
    def cap(mm, t):
        return sum(dias_consumidos_aprox(t, c, mo) * mm.x[c, t, mo] for c in mm.C for mo in mm.M) <= DIAS_MAX
    m.CAP = pyo.Constraint(m.T, rule=cap)

    solver = pyo.SolverFactory("cbc", executable=CBC_EXE)
    solver.solve(m, tee=False)

    y_val = {c: int(pyo.value(m.y[c]) > 0.5) for c in C_REG}
    assign = {}   # (t,c)->1
    mode = {}
    rows = []
    for c in C_REG:
        for t in TECNICOS:
            for mo in MODOS:
                if pyo.value(m.x[c, t, mo]) > 0.5:
                    assign[(t, c)] = 1
                    mode[(t, c)] = mo
                    rows.append([c, t, mo, costo_interno_aprox_uf(t, c, mo), dias_consumidos_aprox(t, c, mo)])

    df = pd.DataFrame(rows, columns=["ciudad", "tecnico", "modo", "costo_aprox_fase1_uf", "dias_aprox_fase1"])
    df.to_excel(os.path.join(OUTPUTS_DIR, "resultado_optimizacion_gps_fase1.xlsx"), index=False)

    return {"I_reg": y_val, "assign": assign, "mode": mode}

# =========================
# 7) FASE 2 – SIMULACIÓN OPERATIVA (GPS enteros)
# =========================
def build_initial_solution(ws):
    city_type = {c: "externo" for c in CIUDADES}
    city_type[SANTIAGO] = "mixto_scl"  # siempre mixto

    for c, v in ws["I_reg"].items():
        city_type[c] = "interno" if v == 1 else "externo"

    tech_cities = {t: [] for t in TECNICOS}
    for (t, c), _ in ws["assign"].items():
        tech_cities[t].append(c)

    return city_type, tech_cities

def simulate_tech_schedule(tecnico: str, cities_list: list[str], gps_asignados: dict[str, int]):
    """
    Simula día a día:
    - Estado por ciudad = GPS pendientes (enteros).
    - Opción A viaje: si tv > hh_día => día solo viaje; duerme destino; instala al siguiente.
    """
    base = base_tecnico(tecnico)
    hd = horas_diarias(tecnico)
    gpd = gps_por_dia(tecnico)

    if hd <= 1e-9 or gpd <= 0:
        return [], {"total_uf": 1e18}, False

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
    }

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1, DIAS_MAX)

    pending = {c: int(max(0, gps_asignados.get(c, 0))) for c in cities_list}

    def choose_mode(o, d):
        if o == d:
            return "terrestre"
        road = costo_viaje_uf(o, d, "terrestre")
        air = costo_viaje_uf(o, d, "avion")
        return "avion" if air < road else "terrestre"

    def can_install_today(time_left_h: float) -> int:
        return int(math.floor(time_left_h / max(1e-9, TIEMPO_INST_GPS_H)))

    for c in cities_list:
        if pending.get(c, 0) <= 0:
            continue
        if day > DIAS_MAX:
            break

        # Modo entrada desde donde durmió
        modo_in = choose_mode(sleep_city, c)
        tv = t_viaje(sleep_city, c, modo_in)
        cv = costo_viaje_uf(sleep_city, c, modo_in)

        # costos del día (aunque sea solo viaje)
        cost["travel_uf"] += cv
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia

        # flete (una vez por ciudad cuando entras a esa ciudad por primera vez como interno)
        # (si tu regla es otra, se ajusta aquí)
        if flete_aplica(c, base, modo_in):
            cost["flete_uf"] += safe_float(FLETE_UF.get(c, 0.0), 0.0)

        # Opción A: si el viaje consume el día completo => no instala hoy
        if tv > hd and sleep_city != c:
            sleep_city = c
            if sleep_city != base:
                cost["aloj_uf"] += ALOJ_UF

            plan.append({
                "tecnico": tecnico,
                "dia": day,
                "ciudad_trabajo": c,
                "horas_instal": 0.0,
                "gps_inst": 0,
                "viaje_modo_manana": modo_in,
                "viaje_h_manana": tv,
                "duerme_en": sleep_city,
                "nota": "Día solo viaje (tv>hh_dia)"
            })
            day += 1
            if day > DIAS_MAX:
                break
            # al día siguiente entra ya en la ciudad sin viaje
            modo_in = None
            tv = 0.0

        # instala lo que alcance (GPS enteros)
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
            "tecnico": tecnico,
            "dia": day,
            "ciudad_trabajo": c,
            "horas_instal": horas_instal,
            "gps_inst": int(gps_inst),
            "viaje_modo_manana": modo_in,
            "viaje_h_manana": tv,
            "duerme_en": sleep_city,
            "nota": ""
        })
        day += 1

        # días siguientes en misma ciudad
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
                "tecnico": tecnico,
                "dia": day,
                "ciudad_trabajo": c,
                "horas_instal": horas_instal,
                "gps_inst": int(gps_inst),
                "viaje_modo_manana": None,
                "viaje_h_manana": 0.0,
                "duerme_en": sleep_city,
                "nota": ""
            })
            day += 1

    feasible = (day - 1) <= DIAS_MAX
    cost["total_uf"] = sum(v for k, v in cost.items() if k != "total_uf")
    return plan, cost, feasible

def allocate_gps_work(tech_cities: dict[str, list[str]]):
    """
    Asignación GPS (enteros):
    1) Base-first: cada técnico instala primero en su base (si hay demanda).
    2) Luego instala sus ciudades internas asignadas (regiones), hasta su capacidad.
    Retorna:
      gps_asignados[t][ciudad] = gps
      rem_gps[ciudad] = gps que quedan para externo
    """
    rem_gps = {c: int(max(0, GPS_TOTAL.get(c, 0))) for c in CIUDADES}
    gps_asignados = {t: defaultdict(int) for t in TECNICOS}

    # técnicos por base
    tech_by_base = defaultdict(list)
    for t in TECNICOS:
        tech_by_base[base_tecnico(t)].append(t)

    # 1) base-first
    for base_city, techs in tech_by_base.items():
        if rem_gps.get(base_city, 0) <= 0:
            continue
        for t in techs:
            cap = capacidad_gps_tecnico(t)
            used = sum(gps_asignados[t].values())
            free = max(0, cap - used)
            if free <= 0:
                continue
            take = min(rem_gps[base_city], free)
            if take > 0:
                gps_asignados[t][base_city] += int(take)
                rem_gps[base_city] -= int(take)
            if rem_gps[base_city] <= 0:
                break

    # 2) regiones internas asignadas por fase1
    for t, clist in tech_cities.items():
        cap = capacidad_gps_tecnico(t)
        used = sum(gps_asignados[t].values())
        free = max(0, cap - used)
        if free <= 0:
            continue

        for c in clist:
            if c == SANTIAGO:
                continue
            need = rem_gps.get(c, 0)
            if need <= 0:
                continue
            if free <= 0:
                break

            take = min(need, free)
            gps_asignados[t][c] += int(take)
            rem_gps[c] -= int(take)
            free -= int(take)

    return gps_asignados, rem_gps

def total_cost_solution(city_type, tech_cities):
    gps_asignados, rem_gps = allocate_gps_work(tech_cities)

    total = 0.0

    # costos internos (operación)
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

    # costos externos (remanente)
    for c in CIUDADES:
        gps_ext = int(max(0, rem_gps.get(c, 0)))
        ext = costo_externo_uf(c, gps_externos=gps_ext)
        total += ext["total_externo_sin_materiales_uf"]

    # materiales (siempre)
    total += sum(costo_materiales_ciudad(c) for c in CIUDADES)

    return total

def improve_solution(city_type, tech_cities, iters=400, seed=42):
    best_ct = deepcopy(city_type)
    best_tc = deepcopy(tech_cities)
    best_cost = total_cost_solution(best_ct, best_tc)

    rng = np.random.default_rng(seed)
    cities_no_scl = [c for c in CIUDADES if c != SANTIAGO]

    for _ in range(iters):
        ct2 = deepcopy(best_ct)
        tc2 = deepcopy(best_tc)

        move_type = int(rng.integers(0, 2))  # 0 flip, 1 reassign

        # flip externo <-> interno (solo regiones)
        if move_type == 0:
            c = str(rng.choice(cities_no_scl))

            if ct2.get(c) == "interno":
                ct2[c] = "externo"
                for t in TECNICOS:
                    if c in tc2[t]:
                        tc2[t].remove(c)
            else:
                # probar asignar a un técnico
                best_t = None
                best_val = 1e18
                for t in TECNICOS:
                    if c in tc2[t]:
                        continue
                    tc_trial = deepcopy(tc2)
                    tc_trial[t] = tc_trial[t] + [c]
                    ct_trial = deepcopy(ct2)
                    ct_trial[c] = "interno"
                    val = total_cost_solution(ct_trial, tc_trial)
                    if val < best_val:
                        best_val = val
                        best_t = t
                if best_t is None:
                    continue
                ct2[c] = "interno"
                tc2[best_t].append(c)

        # reasignar ciudad interna entre técnicos
        else:
            donors = [t for t in TECNICOS if len(tc2[t]) > 0]
            if not donors:
                continue
            t_from = str(rng.choice(donors))
            c = str(rng.choice(tc2[t_from]))
            t_to = str(rng.choice([t for t in TECNICOS if t != t_from]))

            tc2[t_from].remove(c)
            tc2[t_to].append(c)

        new_cost = total_cost_solution(ct2, tc2)
        if new_cost + 1e-6 < best_cost:
            best_cost = new_cost
            best_ct = ct2
            best_tc = tc2

    return best_ct, best_tc, best_cost

# =========================
# 8) RUN + EXPORT
# =========================
def run_all():
    print(f"[INFO] CBC_EXE = {CBC_EXE}")

    ws = solve_phase1()
    city_type, tech_cities = build_initial_solution(ws)

    city_type2, tech_cities2, best_cost = improve_solution(city_type, tech_cities, iters=400)

    gps_asignados, rem_gps = allocate_gps_work(tech_cities2)

    # Validación dura: gps_inst debe ser entero sí o sí (por diseño)
    # (esta validación la haremos después de construir df_plan)

    # Export
    plan_rows = []
    cost_rows = []
    city_rows = []

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
            "materiales_uf": 0.0,
            "pxq_uf": 0.0,
            "total_uf": cst["total_uf"],
        })

    # externos por ciudad (remanente)
    for c in CIUDADES:
        gps_ext = int(max(0, rem_gps.get(c, 0)))
        ext = costo_externo_uf(c, gps_externos=gps_ext)

        city_rows.append({
            "ciudad": c,
            "tipo_ciudad_final": ("mixto_scl" if c == SANTIAGO else city_type2.get(c, "externo")),
            "gps_total": int(max(0, GPS_TOTAL.get(c, 0))),
            "gps_internos": int(max(0, GPS_TOTAL.get(c, 0) - gps_ext)),
            "gps_externos": gps_ext,
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
            "materiales_uf": 0.0,
            "pxq_uf": ext["pxq_uf"],
            "total_uf": ext["total_externo_sin_materiales_uf"],
        })

    # materiales como fila única (para que el total cierre y quede auditado)
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
        "materiales_uf": materiales_total,
        "pxq_uf": 0.0,
        "total_uf": materiales_total,
    })

    # dataframes
    df_tipo = pd.DataFrame([{
        "ciudad": c,
        "tipo_final": ("mixto_scl" if c == SANTIAGO else city_type2.get(c, "externo"))
    } for c in CIUDADES])

    df_plan = pd.DataFrame(plan_rows)
    if df_plan.empty:
        df_plan = pd.DataFrame(columns=[
            "tecnico", "dia", "ciudad_trabajo", "horas_instal", "gps_inst",
            "viaje_modo_manana", "viaje_h_manana", "duerme_en", "nota"
        ])
    else:
        df_plan = df_plan.sort_values(["tecnico", "dia"]).reset_index(drop=True)
        # VALIDACIÓN DURA: gps_inst entero
        gps_float = df_plan["gps_inst"].astype(float)
        if not np.all(gps_float == np.floor(gps_float)):
            raise RuntimeError("gps_inst tiene decimales (modelo inválido). Debe ser entero.")
        df_plan["gps_inst"] = df_plan["gps_inst"].astype(int)

    df_cost = pd.DataFrame(cost_rows)
    df_cost = df_cost.sort_values(["tipo", "total_uf"], ascending=[True, False])

    df_city = pd.DataFrame(city_rows).sort_values(["total_ciudad_uf"], ascending=False)

    total_uf = df_cost["total_uf"].sum()
    resumen = {
        "total_uf": total_uf,
        "total_interno_uf": df_cost.loc[df_cost["tipo"] == "INTERNO", "total_uf"].sum(),
        "total_externo_sin_materiales_uf": df_cost.loc[df_cost["tipo"] == "EXTERNO", "total_uf"].sum(),
        "materiales_total_uf": materiales_total,
        "gps_total": sum(int(max(0, GPS_TOTAL.get(c, 0))) for c in CIUDADES),
        "dias_max_proyecto": DIAS_MAX,
        "dias_semana": DIAS_SEM,
        "horas_jornada": H_DIA,
        "tiempo_inst_gps_h": TIEMPO_INST_GPS_H,
        "nota_unidades": "Inputs en UF. hh_semana_proyecto interpretado como DÍAS/SEMANA. GPS discretos enteros.",
        "nota_viaje": "Opción A: si tv > hh_día => día solo viaje, duerme destino, instala al siguiente.",
        "nota_santiago": "Santiago mixto: técnicos base instalan parte; remanente queda externo.",
    }
    df_resumen = pd.DataFrame(list(resumen.items()), columns=["metric", "value"])

    out_path = os.path.join(OUTPUTS_DIR, "plan_global_operativo.xlsx")
    with pd.ExcelWriter(out_path) as w:
        df_resumen.to_excel(w, index=False, sheet_name="Resumen_Total")
        df_tipo.to_excel(w, index=False, sheet_name="Tipo_Ciudad_Final")
        df_city.to_excel(w, index=False, sheet_name="Costos_por_Ciudad")
        df_plan.to_excel(w, index=False, sheet_name="Plan_Diario")
        df_cost.to_excel(w, index=False, sheet_name="Costos_Detalle")

    print("[OK] ->", out_path)
    print("[OK] Costo total (UF):", round(total_uf, 4))
    print("[OK] (debug) best_cost evaluator (UF):", round(best_cost, 4))

if __name__ == "__main__":
    run_all()
