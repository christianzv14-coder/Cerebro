# modelo_optimizacion_gps_chile_FINAL.py
# Optimización costos instalación GPS (Chile) – FINAL
# FIX CLAVE: hh_semana_proyecto viene en DÍAS/SEMANA (no horas/semana)
# + Santiago MIXTO real (internos instalan parte en base y el resto puede quedar externo)
# + Opción A viaje: si tv > hh_día => ese día SOLO viaja, duerme en destino y trabaja al día siguiente
# + Costos: internos + externos + materiales (siempre) + incentivos + viajes + alojamientos + almuerzos + sueldo prorateado
#
# Requiere: pandas, numpy, openpyxl, pyomo, pulp (CBC)
# Inputs en ./data/
# Outputs en ./outputs/

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

CBC_EXE = pulp.apis.PULP_CBC_CMD().path  # ruta al cbc que usa PuLP

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
peajes = pd.read_excel(os.path.join(PATH, "matriz_peajes.xlsx"), index_col=0)
avion_cost = pd.read_excel(os.path.join(PATH, "matriz_costo_avion.xlsx"), index_col=0)
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

# OJO: todos los inputs vienen en UF (incl. flete, peajes, avión, pxq, sueldos, etc.)
H_DIA = safe_float(param.get("horas_jornada"), 7.0)
VEL = safe_float(param.get("velocidad_terrestre"), 80.0)
TIEMPO_INST_GPS_H = safe_float(param.get("tiempo_instalacion_gps"), 1.25)

DIAS_SEM = int(safe_float(param.get("dias_semana"), 6))
SEMANAS = int(safe_float(param.get("semanas_proyecto"), 4))
DIAS_MAX = DIAS_SEM * SEMANAS

HH_MES = safe_float(param.get("hh_mes"), 180.0)

# Costos (UF)
ALOJ_UF = safe_float(param.get("alojamiento_uf_noche"), 1.1)
ALMU_UF = safe_float(param.get("almuerzo_uf_dia"), 0.5)
INCENTIVO_UF = safe_float(param.get("incentivo_por_gps"), 1.12)

demanda["vehiculos_1gps"] = demanda["vehiculos_1gps"].fillna(0).astype(float)
demanda["vehiculos_2gps"] = demanda["vehiculos_2gps"].fillna(0).astype(float)

demanda["gps_total"] = demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]
demanda["horas_total"] = TIEMPO_INST_GPS_H * demanda["gps_total"]

H_TOTAL = dict(zip(demanda["ciudad"], demanda["horas_total"]))         # horas totales por ciudad
GPS_TOTAL = dict(zip(demanda["ciudad"], demanda["gps_total"]))          # gps totales por ciudad
V1 = dict(zip(demanda["ciudad"], demanda["vehiculos_1gps"]))            # veh 1GPS
V2 = dict(zip(demanda["ciudad"], demanda["vehiculos_2gps"]))            # veh 2GPS

# Kits (UF)
kits["tipo_kit"] = kits["tipo_kit"].astype(str)
KIT1_UF = safe_float(kits.loc[kits["tipo_kit"] == "1_GPS", "costo"].values[0], 0.0)
KIT2_UF = safe_float(kits.loc[kits["tipo_kit"] == "2_GPS", "costo"].values[0], 0.0)

def costo_materiales_ciudad(ciudad: str) -> float:
    return KIT1_UF * safe_float(V1.get(ciudad, 0.0), 0.0) + KIT2_UF * safe_float(V2.get(ciudad, 0.0), 0.0)

pxq["ciudad"] = pxq["ciudad"].apply(norm_city)
flete["ciudad"] = flete["ciudad"].apply(norm_city)

# PXQ externo en UF POR GPS (confirmado por ti)
PXQ_UF_POR_GPS = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))  # UF/GPS

# Flete en UF por ciudad (ya viene UF, NO dividir por UF)
FLETE_UF = dict(zip(flete["ciudad"], flete["costo_flete"]))  # UF

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
    # horas semana / días semana
    return horas_semana_proyecto(tecnico) / max(1e-9, DIAS_SEM)

def horas_totales_disponibles(tecnico: str) -> float:
    return horas_diarias(tecnico) * DIAS_MAX

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
        # peajes ya en UF; km no tiene costo bencina aquí porque dijiste todo UF ya está armado en matrices
        # Si tu matriz km es solo distancia, entonces el costo variable debe venir en otra columna.
        # Como tu set de inputs “ya está en UF”, dejamos viaje terrestre = peajes (UF) y el resto está embebido en tu estructura.
        # Si quieres bencina explícita, se agrega como parámetro UF/km.
        peaje_uf = safe_float(peajes.loc[ciudad_origen, ciudad_destino], 0.0)
        return peaje_uf
    return safe_float(avion_cost.loc[ciudad_origen, ciudad_destino], 0.0)

def costo_sueldo_proyecto_uf(tecnico: str) -> float:
    sueldo_mes = safe_float(internos.loc[internos["tecnico"] == tecnico, "sueldo_uf"].values[0], 0.0)
    hh_proy = horas_semana_proyecto(tecnico) * SEMANAS
    return sueldo_mes * (hh_proy / max(1e-9, HH_MES))

def externo_costo_ciudad(ciudad: str, gps_externos: float) -> float:
    """Costo externo variable por GPS + flete si hay algo externo + materiales (siempre)"""
    pxq_uf = safe_float(PXQ_UF_POR_GPS.get(ciudad, 0.0), 0.0) * max(0.0, gps_externos)
    flete_uf = safe_float(FLETE_UF.get(ciudad, 0.0), 0.0) if gps_externos > 1e-9 else 0.0
    mat_uf = costo_materiales_ciudad(ciudad)  # siempre (se instala igual)
    return pxq_uf + flete_uf + mat_uf

# =========================
# 6) FASE 1 – MILP (solo decide INTERNAL vs EXTERNAL por ciudad fuera de Santiago)
# =========================
def solve_phase1():
    # ciudades sin Santiago para decisión “binaria”
    C_REG = [c for c in CIUDADES if c != SANTIAGO]

    # precomputos lineales
    # costo interno aproximado por ciudad = (viaje base->ciudad + aloj+alm+incentivo+sueldo prorrateado + flete si aplica) + materiales
    # aproximación por ciudad (sin secuencia), para MILP warm start.
    def costo_interno_aprox_ciudad(tecnico: str, ciudad: str, modo: str) -> float:
        base = base_tecnico(tecnico)
        hd = horas_diarias(tecnico)
        if hd <= 1e-9:
            return 1e12

        # Opción A viaje: si tv > hd => el primer día solo viaja, luego instala
        tv = t_viaje(base, ciudad, modo)
        viaje_uf = costo_viaje_uf(base, ciudad, modo)

        horas_ciudad = safe_float(H_TOTAL.get(ciudad, 0.0), 0.0)
        dias_instal = int(math.ceil(horas_ciudad / max(1e-9, hd))) if horas_ciudad > 1e-9 else 1

        # si el viaje consume todo el día: +1 día de viaje (sin instalar)
        dias_total = dias_instal
        if tv > hd and ciudad != base:
            dias_total += 1

        sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
        sueldo_dia = sueldo_proy / max(1, DIAS_MAX)

        # costos base por días
        alm = ALMU_UF * dias_total
        alo = ALOJ_UF * dias_total if ciudad != base else 0.0
        inc = INCENTIVO_UF * safe_float(GPS_TOTAL.get(ciudad, 0.0), 0.0)
        sue = sueldo_dia * dias_total

        # flete solo si no es Santiago o si modo avión; aquí ciudad != Santiago siempre
        flete_uf = safe_float(FLETE_UF.get(ciudad, 0.0), 0.0)

        mat = costo_materiales_ciudad(ciudad)

        return viaje_uf + alm + alo + inc + sue + flete_uf + mat

    # días aproximados consumidos del proyecto por técnico para capacidad
    def dias_consumidos_aprox(tecnico: str, ciudad: str, modo: str) -> float:
        base = base_tecnico(tecnico)
        hd = horas_diarias(tecnico)
        if hd <= 1e-9:
            return 1e12

        tv = t_viaje(base, ciudad, modo)
        horas_ciudad = safe_float(H_TOTAL.get(ciudad, 0.0), 0.0)
        dias_instal = int(math.ceil(horas_ciudad / max(1e-9, hd))) if horas_ciudad > 1e-9 else 1
        dias_total = dias_instal
        if tv > hd and ciudad != base:
            dias_total += 1
        return dias_total

    if not CBC_EXE or not os.path.exists(CBC_EXE):
        raise RuntimeError("No se encontró CBC vía PuLP. Reinstala pulp o revisa PULP_CBC_CMD().path")

    m = pyo.ConcreteModel()
    m.C = pyo.Set(initialize=C_REG)
    m.T = pyo.Set(initialize=TECNICOS)
    m.M = pyo.Set(initialize=MODOS)

    # x[c,t,mo]=1 si ciudad c se cubre INTERNAMENTE por técnico t con modo mo (aprox)
    m.x = pyo.Var(m.C, m.T, m.M, domain=pyo.Binary)
    # y[c]=1 si ciudad c es interna, 0 si externa
    m.y = pyo.Var(m.C, domain=pyo.Binary)

    # Objetivo lineal
    def obj_rule(mm):
        cost = 0.0
        for c in mm.C:
            # costo interno si se decide interno (vía alguna x)
            cost += sum(mm.x[c, t, mo] * costo_interno_aprox_ciudad(t, c, mo) for t in mm.T for mo in mm.M)
            # costo externo si y=0 (todo externo en esa ciudad)
            cost += (1 - mm.y[c]) * externo_costo_ciudad(c, gps_externos=safe_float(GPS_TOTAL.get(c, 0.0), 0.0))
        return cost

    m.OBJ = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

    # linking x <= y
    def link_xy(mm, c, t, mo):
        return mm.x[c, t, mo] <= mm.y[c]
    m.LINK = pyo.Constraint(m.C, m.T, m.M, rule=link_xy)

    # si y=1 => exactamente una asignación (un técnico + un modo) para c
    def unica(mm, c):
        return sum(mm.x[c, t, mo] for t in mm.T for mo in mm.M) == mm.y[c]
    m.UNICA = pyo.Constraint(m.C, rule=unica)

    # capacidad por técnico (días totales consumidos)
    def cap(mm, t):
        return sum(dias_consumidos_aprox(t, c, mo) * mm.x[c, t, mo] for c in mm.C for mo in mm.M) <= DIAS_MAX
    m.CAP = pyo.Constraint(m.T, rule=cap)

    solver = pyo.SolverFactory("cbc", executable=CBC_EXE)
    res = solver.solve(m, tee=False)

    y_val = {c: int(pyo.value(m.y[c]) > 0.5) for c in C_REG}
    assign = {}  # (t,c)->1
    mode = {}
    rows = []
    for c in C_REG:
        for t in TECNICOS:
            for mo in MODOS:
                if pyo.value(m.x[c, t, mo]) > 0.5:
                    assign[(t, c)] = 1
                    mode[(t, c)] = mo
                    rows.append([c, t, mo, costo_interno_aprox_ciudad(t, c, mo), dias_consumidos_aprox(t, c, mo)])

    df = pd.DataFrame(rows, columns=["ciudad", "tecnico", "modo", "costo_aprox_fase1_uf", "dias_aprox_fase1"])
    df.to_excel(os.path.join(OUTPUTS_DIR, "resultado_optimizacion_gps_fase1.xlsx"), index=False)

    return {"I_reg": y_val, "assign": assign, "mode": mode}

# =========================
# 7) FASE 2 – SIMULACIÓN OPERATIVA (secuencia real)
#     - Santiago MIXTO: los técnicos con base Santiago instalan en Santiago lo que alcancen (base primero),
#       el remanente queda externo.
# =========================
def build_initial_solution(ws):
    city_type = {c: "externo" for c in CIUDADES}
    city_type[SANTIAGO] = "mixto_scl"  # siempre mixto: puede absorber internos y dejar remanente externo

    # ciudades internas decididas en fase 1 (regiones)
    for c, v in ws["I_reg"].items():
        city_type[c] = "interno" if v == 1 else "externo"

    tech_cities = {t: [] for t in TECNICOS}
    for (t, c), _ in ws["assign"].items():
        tech_cities[t].append(c)

    return city_type, tech_cities

def simulate_tech_schedule(tecnico: str, cities_list: list[str], horas_asignadas: dict[str, float]):
    """
    Simula día a día.
    - horas_asignadas[c] indica cuántas horas DE ESA CIUDAD le asignamos a este técnico (puede ser parcial para base).
    - Opción A viaje: si tv > hh_día => día solo viaje; duerme destino; instala al día siguiente.
    """
    base = base_tecnico(tecnico)
    hd = horas_diarias(tecnico)
    if hd <= 1e-9:
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
    }

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1, DIAS_MAX)

    pending_h = {c: max(0.0, safe_float(horas_asignadas.get(c, 0.0), 0.0)) for c in cities_list}

    def choose_mode(o, d):
        if o == d:
            return "terrestre"
        road = costo_viaje_uf(o, d, "terrestre")
        air = costo_viaje_uf(o, d, "avion")
        return "avion" if air < road else "terrestre"

    for c in cities_list:
        if pending_h.get(c, 0.0) <= 1e-9:
            continue
        if day > DIAS_MAX:
            break

        # 1) viajar (si corresponde) desde donde durmió
        modo_in = choose_mode(sleep_city, c)
        tv = t_viaje(sleep_city, c, modo_in)
        cv = costo_viaje_uf(sleep_city, c, modo_in)

        # costos del día sí o sí (almuerzo + sueldo + viaje si aplica)
        cost["travel_uf"] += cv
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia

        # Opción A: si tv > hd => día solo viaje
        if tv > hd and sleep_city != c:
            sleep_city = c
            if sleep_city != base:
                cost["aloj_uf"] += ALOJ_UF

            plan.append({
                "tecnico": tecnico,
                "dia": day,
                "ciudad_trabajo": c,
                "horas_instal": 0.0,
                "gps_inst": 0.0,
                "viaje_modo_manana": modo_in,
                "viaje_h_manana": tv,
                "duerme_en": sleep_city,
                "nota": "Dia solo viaje (tv>hh_dia)"
            })
            day += 1
            if day > DIAS_MAX:
                break
            # al día siguiente sigue con instalación en esta ciudad (sin viaje)
            modo_in = None
            tv = 0.0

        # 2) instalar el mismo día (si alcanza)
        time_left = max(0.0, hd - tv)
        installed = min(pending_h[c], time_left)
        pending_h[c] -= installed
        gps_inst = installed / max(1e-9, TIEMPO_INST_GPS_H)
        cost["inc_uf"] += INCENTIVO_UF * gps_inst

        sleep_city = c
        if sleep_city != base:
            cost["aloj_uf"] += ALOJ_UF

        plan.append({
            "tecnico": tecnico,
            "dia": day,
            "ciudad_trabajo": c,
            "horas_instal": installed,
            "gps_inst": gps_inst,
            "viaje_modo_manana": modo_in,
            "viaje_h_manana": tv,
            "duerme_en": sleep_city,
            "nota": ""
        })
        day += 1

        # 3) días siguientes en la misma ciudad hasta terminar
        while pending_h[c] > 1e-9 and day <= DIAS_MAX:
            installed = min(pending_h[c], hd)
            pending_h[c] -= installed
            gps_inst = installed / max(1e-9, TIEMPO_INST_GPS_H)

            cost["alm_uf"] += ALMU_UF
            cost["sueldo_uf"] += sueldo_dia
            cost["inc_uf"] += INCENTIVO_UF * gps_inst

            if sleep_city != base:
                cost["aloj_uf"] += ALOJ_UF

            plan.append({
                "tecnico": tecnico,
                "dia": day,
                "ciudad_trabajo": c,
                "horas_instal": installed,
                "gps_inst": gps_inst,
                "viaje_modo_manana": None,
                "viaje_h_manana": 0.0,
                "duerme_en": sleep_city,
                "nota": ""
            })
            day += 1

    feasible = (day - 1) <= DIAS_MAX
    cost["total_uf"] = sum(v for k, v in cost.items() if k != "total_uf")
    return plan, cost, feasible

def allocate_base_city_work(tech_cities: dict[str, list[str]]):
    """
    Santiago MIXTO (y también aplica para otras bases si hay demanda en base):
    - asigna horas de la base a los técnicos que tienen esa base, respetando su capacidad total.
    - esto permite: instala en base y luego viajar a otras ciudades.
    Retorna:
      horas_asignadas_por_tecnico: dict[t][ciudad] = horas
      remanente_h_por_ciudad: dict[ciudad] = horas que quedan para externos
    """
    rem_h = {c: safe_float(H_TOTAL.get(c, 0.0), 0.0) for c in CIUDADES}
    horas_asignadas = {t: defaultdict(float) for t in TECNICOS}

    # agrupamos técnicos por base
    tech_by_base = defaultdict(list)
    for t in TECNICOS:
        tech_by_base[base_tecnico(t)].append(t)

    # asignación base-first
    for base_city, techs in tech_by_base.items():
        if rem_h.get(base_city, 0.0) <= 1e-9:
            continue
        # asignamos secuencialmente (estable, determinístico)
        for t in techs:
            cap_h = horas_totales_disponibles(t)
            already = sum(horas_asignadas[t].values())
            free_h = max(0.0, cap_h - already)
            if free_h <= 1e-9:
                continue
            take = min(rem_h[base_city], free_h)
            if take > 1e-9:
                horas_asignadas[t][base_city] += take
                rem_h[base_city] -= take
            if rem_h[base_city] <= 1e-9:
                break

    # ahora asignación de ciudades internas (regiones) según tech_cities
    for t, clist in tech_cities.items():
        cap_h = horas_totales_disponibles(t)
        already = sum(horas_asignadas[t].values())
        free_h = max(0.0, cap_h - already)

        for c in clist:
            if c == SANTIAGO:
                continue
            need = rem_h.get(c, 0.0)
            if need <= 1e-9:
                continue
            if free_h <= 1e-9:
                break

            take = min(need, free_h)
            horas_asignadas[t][c] += take
            rem_h[c] -= take
            free_h -= take

    return horas_asignadas, rem_h

def total_cost_solution(city_type, tech_cities):
    # asignación base + regiones internas (en horas)
    horas_asignadas, rem_h = allocate_base_city_work(tech_cities)

    total = 0.0

    # costos internos (viajes + aloj + alm + incentivo + sueldo) por técnico con su secuencia
    for t in TECNICOS:
        # lista de ciudades a visitar = (base si tiene horas) + (ciudades internas asignadas)
        # orden: base primero, luego las demás como vienen (fase 2 puede reordenar si quieres)
        city_set = [c for c, h in horas_asignadas[t].items() if h > 1e-9]
        if not city_set:
            continue
        # base primero si existe
        base = base_tecnico(t)
        if base in city_set:
            city_set = [base] + [c for c in city_set if c != base]

        plan, cst, feas = simulate_tech_schedule(t, city_set, horas_asignadas[t])
        if not feas:
            return 1e18
        total += cst["total_uf"]

    # costos externos por remanente (PXQ por GPS externo + flete si aplica + materiales siempre)
    for c in CIUDADES:
        # gps externos estimados por horas remanentes / tiempo instalación
        gps_ext = max(0.0, rem_h.get(c, 0.0) / max(1e-9, TIEMPO_INST_GPS_H))
        total += externo_costo_ciudad(c, gps_externos=gps_ext)

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

        # MOVE 0: flip externo <-> interno (solo regiones; Santiago siempre mixto)
        if move_type == 0:
            c = str(rng.choice(cities_no_scl))

            if ct2.get(c) == "interno":
                ct2[c] = "externo"
                for t in TECNICOS:
                    if c in tc2[t]:
                        tc2[t].remove(c)
            else:
                # intentar asignar c a algún técnico (si cabe en capacidad)
                best_t = None
                best_cost_t = 1e18
                for t in TECNICOS:
                    if c in tc2[t]:
                        continue
                    trial = tc2[t] + [c]
                    # evaluamos costo total solución, pero barato: aproximamos con total_cost_solution
                    tc_trial = deepcopy(tc2)
                    tc_trial[t] = trial
                    ct_trial = deepcopy(ct2)
                    ct_trial[c] = "interno"
                    new_cost = total_cost_solution(ct_trial, tc_trial)
                    if new_cost < best_cost_t:
                        best_cost_t = new_cost
                        best_t = t

                if best_t is None:
                    continue
                ct2[c] = "interno"
                tc2[best_t].append(c)

        # MOVE 1: reassign ciudad entre técnicos (solo ciudades internas reales)
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

    # mejora
    city_type2, tech_cities2, best_cost = improve_solution(city_type, tech_cities, iters=400)

    # asignación final base + regiones internas
    horas_asignadas, rem_h = allocate_base_city_work(tech_cities2)

    # Validación: toda ciudad marcada interna (regiones) debe tener horas internas asignadas > 0
    internas_reg = [c for c in CIUDADES if c != SANTIAGO and city_type2.get(c) == "interno"]
    falt = []
    for c in internas_reg:
        ok = False
        for t in TECNICOS:
            if horas_asignadas[t].get(c, 0.0) > 1e-9:
                ok = True
                break
        if not ok:
            falt.append(c)
    if falt:
        raise RuntimeError("Plan inconsistente: ciudades INTERNAS sin horas asignadas: " + ", ".join(falt))

    # Export
    plan_rows = []
    cost_rows = []
    city_cost_rows = []

    # internos por técnico
    for t in TECNICOS:
        clist = [c for c, h in horas_asignadas[t].items() if h > 1e-9]
        if not clist:
            continue
        base = base_tecnico(t)
        if base in clist:
            clist = [base] + [c for c in clist if c != base]

        plan, cst, feas = simulate_tech_schedule(t, clist, horas_asignadas[t])
        if not feas:
            raise RuntimeError(f"Solución final infeasible para técnico {t}")

        plan_rows.extend(plan)
        cost_rows.append({
            "responsable": t,
            "tipo": "INTERNO",
            **{k: v for k, v in cst.items() if k != "total_uf"},
            "total_uf": cst["total_uf"],
        })

    # externos por ciudad (remanente)
    for c in CIUDADES:
        gps_ext = max(0.0, rem_h.get(c, 0.0) / max(1e-9, TIEMPO_INST_GPS_H))
        c_ext = externo_costo_ciudad(c, gps_externos=gps_ext)
        # desglose externo
        pxq_uf = safe_float(PXQ_UF_POR_GPS.get(c, 0.0), 0.0) * gps_ext
        flete_uf = safe_float(FLETE_UF.get(c, 0.0), 0.0) if gps_ext > 1e-9 else 0.0
        mat_uf = costo_materiales_ciudad(c)

        city_cost_rows.append({
            "ciudad": c,
            "tipo_ciudad_final": city_type2.get(c, "externo") if c != SANTIAGO else "mixto_scl",
            "gps_total": safe_float(GPS_TOTAL.get(c, 0.0), 0.0),
            "horas_total": safe_float(H_TOTAL.get(c, 0.0), 0.0),
            "horas_internas": safe_float(H_TOTAL.get(c, 0.0), 0.0) - rem_h.get(c, 0.0),
            "horas_externas": rem_h.get(c, 0.0),
            "gps_externos_est": gps_ext,
            "pxq_uf": pxq_uf,
            "flete_uf": flete_uf,
            "materiales_uf": mat_uf,
            "total_externo_uf": c_ext,
        })

        cost_rows.append({
            "responsable": c,
            "tipo": "EXTERNO",
            "travel_uf": 0.0,
            "aloj_uf": 0.0,
            "alm_uf": 0.0,
            "inc_uf": 0.0,
            "sueldo_uf": 0.0,
            "total_uf": c_ext,
        })

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
        df_plan = df_plan.sort_values(["tecnico", "dia"])

    df_cost = pd.DataFrame(cost_rows)
    df_cost = df_cost.sort_values(["tipo", "total_uf"], ascending=[True, False])

    df_city_cost = pd.DataFrame(city_cost_rows).sort_values(["total_externo_uf"], ascending=False)

    resumen = {
        "total_uf": df_cost["total_uf"].sum(),
        "total_interno_uf": df_cost.loc[df_cost["tipo"] == "INTERNO", "total_uf"].sum(),
        "total_externo_uf": df_cost.loc[df_cost["tipo"] == "EXTERNO", "total_uf"].sum(),
        "materiales_total_uf": sum(costo_materiales_ciudad(c) for c in CIUDADES),
        "gps_total": sum(safe_float(GPS_TOTAL.get(c, 0.0), 0.0) for c in CIUDADES),
        "dias_max_proyecto": DIAS_MAX,
        "dias_semana": DIAS_SEM,
        "horas_jornada": H_DIA,
        "tiempo_inst_gps_h": TIEMPO_INST_GPS_H,
        "nota_unidades": "hh_semana_proyecto se interpreta como DIAS/SEMANA (se multiplica por horas_jornada).",
        "nota_viaje": "Opción A: si tv > hh_día => día solo viaje, duerme destino, instala siguiente día.",
        "nota_santiago": "Santiago es mixto_scl: internos en base pueden instalar parte; remanente va a externo.",
    }
    df_resumen = pd.DataFrame(list(resumen.items()), columns=["metric", "value"])

    out_path = os.path.join(OUTPUTS_DIR, "plan_global_operativo.xlsx")
    with pd.ExcelWriter(out_path) as w:
        df_resumen.to_excel(w, index=False, sheet_name="Resumen_Total")
        df_tipo.to_excel(w, index=False, sheet_name="Tipo_Ciudad_Final")
        df_city_cost.to_excel(w, index=False, sheet_name="Costos_por_Ciudad")
        df_plan.to_excel(w, index=False, sheet_name="Plan_Diario")
        df_cost.to_excel(w, index=False, sheet_name="Costos_Detalle")

    print("[OK] ->", out_path)
    print("[OK] Costo total (UF):", round(df_cost["total_uf"].sum(), 4))
    print("[OK] (debug) best_cost evaluator (UF):", round(best_cost, 4))

if __name__ == "__main__":
    run_all()
