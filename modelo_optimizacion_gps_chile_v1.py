# modelo_optimizacion_gps_chile_v1.py
# Fase 1 (MILP warm start) + Fase 2 (mejora global heurística) – CORREGIDO
# Requiere: pandas, numpy, openpyxl, pyomo, pulp (para ubicar CBC), solver CBC
# Datos en carpeta ./data/

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

# Solver: CBC localizado vía PuLP (no depende de PATH del sistema)
CBC_EXE = pulp.apis.PULP_CBC_CMD().path  # ruta al cbc.exe que usa PuLP

os.makedirs(OUTPUTS_DIR, exist_ok=True)

# =========================
# 1. UTILIDADES (TIPOS)
# =========================
def time_to_hours(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return 0.0
    if isinstance(x, dt_time):
        return x.hour + x.minute / 60.0 + x.second / 3600.0
    return float(x)

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

demanda["gps_total"] = demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]
demanda["horas"] = 0.75 * demanda["gps_total"]

H = dict(zip(demanda["ciudad"], demanda["horas"]))
GPS_TOTAL = dict(zip(demanda["ciudad"], demanda["gps_total"]))

UF = safe_float(param.get("valor_uf"), 1.0)
PRECIO_BENCINA = safe_float(param.get("precio_bencina"), 0.0)
ALOJ_UF = safe_float(param.get("alojamiento_uf_noche"), 0.0)
ALMU_UF = safe_float(param.get("almuerzo_uf_dia"), 0.0)
INCENTIVO_UF = safe_float(param.get("incentivo_por_gps"), 0.0)
H_DIA = safe_float(param.get("horas_jornada"), 7.0)
VEL = safe_float(param.get("velocidad_terrestre"), 80.0)
DIAS_SEM = int(safe_float(param.get("dias_semana"), 6))
SEMANAS = int(safe_float(param.get("semanas_proyecto"), 4))
DIAS_MAX = DIAS_SEM * SEMANAS
HH_MES = safe_float(param.get("hh_mes"), 180.0)

pxq["ciudad"] = pxq["ciudad"].apply(norm_city)
flete["ciudad"] = flete["ciudad"].apply(norm_city)

PXQ_UF = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))
FLETE = dict(zip(flete["ciudad"], flete["costo_flete"]))  # asumes UF (según tu ajuste Excel)

# =========================
# 5. FUNCIONES AUXILIARES
# =========================
def base_tecnico(tecnico: str) -> str:
    return internos.loc[internos["tecnico"] == tecnico, "ciudad_base"].values[0]

def hh_semana(tecnico: str) -> float:
    return safe_float(internos.loc[internos["tecnico"] == tecnico, "hh_semana_proyecto"].values[0], 0.0)

def alpha_tecnico(tecnico: str) -> float:
    denom = max(1e-9, DIAS_SEM * H_DIA)
    return hh_semana(tecnico) / denom

def horas_diarias(tecnico: str) -> float:
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
        peaje = safe_float(peajes.loc[ciudad_origen, ciudad_destino], 0.0)
        clp = dist_km * PRECIO_BENCINA + peaje
        return clp / max(1e-9, UF)
    clp = safe_float(avion_cost.loc[ciudad_origen, ciudad_destino], 0.0)
    return clp / max(1e-9, UF)

def dias_ciudad(ciudad: str, tecnico: str, modo: str, origen: str) -> int:
    tv = t_viaje(origen, ciudad, modo)
    hd = horas_diarias(tecnico)
    h_dia1 = max(0.0, hd - tv)
    rem = max(0.0, H[ciudad] - h_dia1)
    if rem <= 1e-9:
        return 1
    return 1 + int(math.ceil(rem / max(1e-9, hd)))

def costo_sueldo_proyecto_uf(tecnico: str) -> float:
    sueldo_mes = safe_float(internos.loc[internos["tecnico"] == tecnico, "sueldo_uf"].values[0], 0.0)
    hh_proy = hh_semana(tecnico) * SEMANAS
    return sueldo_mes * (hh_proy / max(1e-9, HH_MES))

def costo_externo_ciudad(ciudad: str) -> float:
    return safe_float(PXQ_UF.get(ciudad, 0.0), 0.0) + safe_float(FLETE.get(ciudad, 0.0), 0.0)

def costo_interno_base_a_ciudad(ciudad: str, tecnico: str, modo: str) -> float:
    base = base_tecnico(tecnico)
    dias = dias_ciudad(ciudad, tecnico, modo, origen=base)

    costo = 0.0

    # Sueldo proporcional por día (sobre proyecto mensual prorrateado)
    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    costo += sueldo_proy * (dias / DIAS_MAX)

    # Alojamiento solo fuera de base
    if ciudad != base:
        costo += dias * ALOJ_UF

    # Almuerzo e incentivo por GPS
    costo += dias * ALMU_UF
    costo += INCENTIVO_UF * GPS_TOTAL[ciudad]

    # Viaje base->ciudad
    costo += costo_viaje_uf(base, ciudad, modo)

    # Flete: solo NO aplica si base Santiago y viaja terrestre
    if base != SANTIAGO or modo == "avion":
        costo += safe_float(FLETE.get(ciudad, 0.0), 0.0)

    return costo

# =========================
# 6. FASE 1 – MILP (WARM START)
# =========================
def solve_phase1():
    m = pyo.ConcreteModel()
    m.C = pyo.Set(initialize=CIUDADES)
    m.T = pyo.Set(initialize=TECNICOS)
    m.M = pyo.Set(initialize=MODOS)

    m.x = pyo.Var(m.C, m.T, m.M, domain=pyo.Binary)  # interno
    m.y = pyo.Var(m.C, domain=pyo.Binary)            # 1=interno

    def obj_rule(mm):
        cost = 0.0
        for c in mm.C:
            cost += sum(mm.x[c, t, mo] * costo_interno_base_a_ciudad(c, t, mo) for t in mm.T for mo in mm.M)
            cost += (1 - mm.y[c]) * costo_externo_ciudad(c)
        return cost

    m.OBJ = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

    def link_xy(mm, c, t, mo):
        return mm.x[c, t, mo] <= mm.y[c]
    m.LINK = pyo.Constraint(m.C, m.T, m.M, rule=link_xy)

    def unica_ciudad(mm, c):
        if c == SANTIAGO:
            return pyo.Constraint.Skip
        return sum(mm.x[c, t, mo] for t in mm.T for mo in mm.M) == mm.y[c]
    m.UNICA = pyo.Constraint(m.C, rule=unica_ciudad)

    def one_tech_per_city(mm, c):
        if c == SANTIAGO:
            return pyo.Constraint.Skip
        return sum(mm.x[c, t, mo] for t in mm.T for mo in mm.M) <= 1
    m.ONE = pyo.Constraint(m.C, rule=one_tech_per_city)

    def santiago_cap(mm):
        return sum(mm.x[SANTIAGO, t, mo] for t in mm.T for mo in mm.M) <= 5
    m.SCLCAP = pyo.Constraint(rule=santiago_cap)

    def capacidad(mm, t):
        base = base_tecnico(t)
        return sum(dias_ciudad(c, t, mo, origen=base) * mm.x[c, t, mo] for c in mm.C for mo in mm.M) <= DIAS_MAX
    m.CAP = pyo.Constraint(m.T, rule=capacidad)

    if not CBC_EXE or not os.path.exists(CBC_EXE):
        raise RuntimeError(
            "No se encontró cbc.exe vía PuLP. Ejecuta: pip install pulp "
            "y verifica pulp.apis.PULP_CBC_CMD().path."
        )

    solver = pyo.SolverFactory("cbc", executable=CBC_EXE)
    solver.solve(m)

    y_val = {c: int(pyo.value(m.y[c]) > 0.5) for c in CIUDADES}
    assign = {}
    mode = {}
    rows = []

    for c in CIUDADES:
        for t in TECNICOS:
            for mo in MODOS:
                if pyo.value(m.x[c, t, mo]) > 0.5:
                    assign[(t, c)] = 1
                    mode[(t, c)] = mo
                    rows.append([
                        c, t, mo,
                        costo_interno_base_a_ciudad(c, t, mo),
                        dias_ciudad(c, t, mo, origen=base_tecnico(t))
                    ])

    df = pd.DataFrame(rows, columns=["ciudad", "tecnico", "modo", "costo_aprox_fase1_uf", "dias_aprox_fase1"])
    df.to_excel(os.path.join(OUTPUTS_DIR, "resultado_optimizacion_gps_fase1.xlsx"), index=False)

    return {"I": y_val, "assign": assign, "mode": mode}

# =========================
# 7. FASE 2 – SIMULACIÓN + MEJORA (2B)
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

    return city_type, tech_cities

def simulate_tech_schedule(tecnico, cities_list):
    base = base_tecnico(tecnico)
    hd = horas_diarias(tecnico)

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
    sueldo_dia = sueldo_proy / DIAS_MAX
    pending_h = {c: H[c] for c in cities_list}

    def flete_aplica(ciudad, modo_llegada):
        # Regla: fletes solo salen desde Santiago hacia afuera.
        # Implementación: solo no aplica si base Santiago y viaja terrestre.
        if base != SANTIAGO:
            return True
        if modo_llegada == "avion":
            return True
        return False

    for c in cities_list:
        if pending_h[c] <= 1e-9:
            continue

        road_cost = costo_viaje_uf(sleep_city, c, "terrestre")
        air_cost = costo_viaje_uf(sleep_city, c, "avion")
        modo_in = "avion" if air_cost < road_cost else "terrestre"

        tv = t_viaje(sleep_city, c, modo_in)
        cv = costo_viaje_uf(sleep_city, c, modo_in)

        if day > DIAS_MAX:
            break

        time_left = max(0.0, hd - tv)

        cost["travel_uf"] += cv
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia

        if flete_aplica(c, modo_in):
            cost["flete_uf"] += safe_float(FLETE.get(c, 0.0), 0.0)

        installed = min(pending_h[c], time_left)
        pending_h[c] -= installed
        gps_inst = installed / 0.75
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
        })

        day += 1

        while pending_h[c] > 1e-9 and day <= DIAS_MAX:
            installed = min(pending_h[c], hd)
            pending_h[c] -= installed
            gps_inst = installed / 0.75

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
            })
            day += 1

    feasible = (day - 1) <= DIAS_MAX
    return plan, cost, feasible

def total_cost_solution(city_type, tech_cities):
    total = 0.0
    for t, clist in tech_cities.items():
        if not clist:
            continue
        _, cst, feas = simulate_tech_schedule(t, clist)
        if not feas:
            return 1e18
        total += sum(cst.values())

    for c in CIUDADES:
        if c == SANTIAGO:
            continue
        if city_type.get(c) == "externo":
            total += costo_externo_ciudad(c)

    return total

def improve_solution(city_type, tech_cities, iters=300, seed=42):
    best_ct = deepcopy(city_type)
    best_tc = deepcopy(tech_cities)
    best_cost = total_cost_solution(best_ct, best_tc)

    rng = np.random.default_rng(seed)
    cities_no_scl = [c for c in CIUDADES if c != SANTIAGO]

    for _ in range(iters):
        ct2 = deepcopy(best_ct)
        tc2 = deepcopy(best_tc)

        move_type = int(rng.integers(0, 2))  # 0 flip, 1 reassign

        # MOVE 0: flip externo <-> interno
        if move_type == 0:
            c = str(rng.choice(cities_no_scl))

            # interno -> externo
            if ct2.get(c) == "interno":
                ct2[c] = "externo"
                for t in TECNICOS:
                    if c in tc2[t]:
                        tc2[t].remove(c)

            # externo -> interno
            else:
                best_t = None
                best_cost_t = 1e18

                for t in TECNICOS:
                    if c in tc2[t]:
                        continue
                    trial = tc2[t] + [c]
                    _, cst, feas = simulate_tech_schedule(t, trial)
                    if not feas:
                        continue
                    cost_t = sum(cst.values())
                    if cost_t < best_cost_t:
                        best_cost_t = cost_t
                        best_t = t

                # clave: si no hay técnico factible -> no tocar nada
                if best_t is None:
                    continue

                # solo aquí confirmamos el flip
                ct2[c] = "interno"
                tc2[best_t].append(c)

        # MOVE 1: reassign ciudad entre técnicos
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
# 8. RUN + EXPORT
# =========================
def run_all():
    print(f"[INFO] CBC_EXE = {CBC_EXE}")

    ws = solve_phase1()
    city_type, tech_cities = build_initial_solution(ws)
    city_type2, tech_cities2, best_cost = improve_solution(city_type, tech_cities, iters=300)

    # ---- Validación dura 1: ciudad interna debe estar asignada (fuera de Santiago)
    internas = [c for c in CIUDADES if c != SANTIAGO and city_type2.get(c) == "interno"]
    asignadas = set()

    n_internas = len(internas)
    print(f"[DEBUG] ciudades internas (sin Santiago) = {n_internas}")

    n_asignaciones = sum(len(v) for v in tech_cities2.values())
    print(f"[DEBUG] total ciudades asignadas a internos = {n_asignaciones}")

    for t, clist in tech_cities2.items():
        for c in clist:
            if c != SANTIAGO:
                asignadas.add(c)

    faltantes = [c for c in internas if c not in asignadas]
    if faltantes:
        raise RuntimeError("Plan inconsistente: ciudades INTERNAS sin técnico asignado: " + ", ".join(faltantes))

    # ---- Validación dura 2: fuera de Santiago, no más de 1 técnico por ciudad
    cnt = Counter()
    for t, clist in tech_cities2.items():
        for c in clist:
            if c != SANTIAGO:
                cnt[c] += 1
    duplicadas = [c for c, k in cnt.items() if k > 1]
    if duplicadas:
        raise RuntimeError("Regla violada: más de un técnico asignado a ciudad (fuera de Santiago): " + ", ".join(duplicadas))

    # ---- Export plan + costos
    plan_rows = []
    cost_rows = []

    for t, clist in tech_cities2.items():
        if not clist:
            continue
        plan, cst, feas = simulate_tech_schedule(t, clist)
        if not feas:
            raise RuntimeError(f"Solución final infeasible para técnico {t}")

        plan_rows.extend(plan)
        cost_rows.append({
            "responsable": t,
            "tipo": "INTERNO",
            **cst,
            "total_uf": sum(cst.values())
        })

    # Externos (cada ciudad externa se paga PxQ + flete)
    for c in CIUDADES:
        if c == SANTIAGO:
            continue
        if city_type2.get(c) == "externo":
            cost_rows.append({
                "responsable": c,
                "tipo": "EXTERNO",
                "travel_uf": 0.0,
                "aloj_uf": 0.0,
                "alm_uf": 0.0,
                "inc_uf": 0.0,
                "sueldo_uf": 0.0,
                "flete_uf": safe_float(FLETE.get(c, 0.0), 0.0),
                "total_uf": costo_externo_ciudad(c),
            })

    # DataFrames robustos
    df_plan = pd.DataFrame(plan_rows)
    print(f"[DEBUG] plan_rows={len(plan_rows)}; df_plan.shape={df_plan.shape}; cols={list(df_plan.columns)}")

    if df_plan.empty:
        df_plan = pd.DataFrame(columns=[
            "tecnico", "dia", "ciudad_trabajo", "horas_instal", "gps_inst",
            "viaje_modo_manana", "viaje_h_manana", "duerme_en"
        ])
    else:
        # ordenar si existen columnas claves
        if "tecnico" in df_plan.columns and "dia" in df_plan.columns:
            df_plan = df_plan.sort_values(["tecnico", "dia"])

    df_cost = pd.DataFrame(cost_rows)
    if df_cost.empty:
        df_cost = pd.DataFrame(columns=[
            "responsable","tipo","travel_uf","aloj_uf","alm_uf","inc_uf","sueldo_uf","flete_uf","total_uf"
        ])
    else:
        df_cost = df_cost.sort_values(["tipo", "total_uf"], ascending=[True, False])

    df_tipo = pd.DataFrame([{"ciudad": c, "tipo_final": city_type2.get(c, "externo")} for c in CIUDADES])

    out_path = os.path.join(OUTPUTS_DIR, "plan_global_operativo.xlsx")
    with pd.ExcelWriter(out_path) as w:
        df_tipo.to_excel(w, index=False, sheet_name="Tipo_Ciudad_Final")
        df_plan.to_excel(w, index=False, sheet_name="Plan_Diario")
        df_cost.to_excel(w, index=False, sheet_name="Costos_Detalle")

    print("OK ->", out_path)
    print("Costo total (UF aprox):", best_cost)

if __name__ == "__main__":
    run_all()
