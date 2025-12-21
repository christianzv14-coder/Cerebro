# modelo_optimizacion_gps_chile_v1.py
# Fase 1 (MILP warm start) + Fase 2 (mejora global heurística)
# Requiere: pandas, numpy, openpyxl, pyomo, solver (cbc/gurobi)
# Datos en carpeta ./data/

import os
import math
from copy import deepcopy
from datetime import time as dt_time

import numpy as np
import pandas as pd
import pyomo.environ as pyo

# =========================
# 0. CONFIG
# =========================
PATH = "data/"
OUTPUTS_DIR = "outputs"
SOLVER = "cbc"  # "cbc" / "glpk" / "gurobi"

SANTIAGO = "Santiago"

os.makedirs(OUTPUTS_DIR, exist_ok=True)

# =========================
# 1. UTILIDADES (TIPOS)
# =========================
def time_to_hours(x):
    """
    Convierte tiempos Excel leídos como datetime.time a horas decimales.
    Soporta:
    - datetime.time -> h + m/60 + s/3600
    - números (float/int) -> float
    - strings numéricas -> float
    """
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
        return float(x)
    except Exception:
        return default

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

def norm_city(x):
    if pd.isna(x):
        return x
    return str(x).strip()

# Normalizar lista maestra de ciudades (demanda manda)
demanda["ciudad"] = demanda["ciudad"].apply(norm_city)
CIUDADES = demanda["ciudad"].tolist()

# Normalizar matrices (index y columnas)
def normalize_matrix(df):
    df.index = df.index.map(norm_city)
    df.columns = df.columns.map(norm_city)
    return df

km = normalize_matrix(km)
peajes = normalize_matrix(peajes)
avion_cost = normalize_matrix(avion_cost)
avion_time = normalize_matrix(avion_time)

# Validación dura: todas las ciudades deben existir en todas las matrices
def check_matrix_coverage(name, df, cities):
    missing_rows = [c for c in cities if c not in df.index]
    missing_cols = [c for c in cities if c not in df.columns]
    if missing_rows or missing_cols:
        print(f"\n[ERROR MATRIZ] {name}")
        if missing_rows:
            print(" - FALTAN FILAS:", missing_rows)
        if missing_cols:
            print(" - FALTAN COLUMNAS:", missing_cols)
        raise ValueError(f"Matriz {name} no cubre todas las ciudades.")

check_matrix_coverage("km", km, CIUDADES)
check_matrix_coverage("peajes", peajes, CIUDADES)
check_matrix_coverage("avion_cost", avion_cost, CIUDADES)
check_matrix_coverage("avion_time", avion_time, CIUDADES)


# =========================
# 3. PARÁMETROS / SETS
# =========================
# Parametros en formato dict
param = param_df.set_index("parametro")["valor"].to_dict()

CIUDADES = demanda["ciudad"].tolist()
TECNICOS = internos["tecnico"].tolist()
MODOS = ["terrestre", "avion"]

# Demanda
demanda["gps_total"] = demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]
demanda["horas"] = 0.75 * demanda["gps_total"]

H = dict(zip(demanda["ciudad"], demanda["horas"]))          # horas requeridas por ciudad
GPS_TOTAL = dict(zip(demanda["ciudad"], demanda["gps_total"]))

# Kits (si los ocupas después)
KIT_COST = {
    "1": safe_float(kits.loc[kits["tipo_kit"] == "1_GPS", "costo"].values[0], 0.0),
    "2": safe_float(kits.loc[kits["tipo_kit"] == "2_GPS", "costo"].values[0], 0.0),
}

# Parámetros globales
UF = safe_float(param.get("valor_uf"), 1.0)
PRECIO_BENCINA = safe_float(param.get("precio_bencina"), 0.0)          # CLP/km (según tu definición)
ALOJ_UF = safe_float(param.get("alojamiento_uf_noche"), 0.0)           # UF/noche
ALMU_UF = safe_float(param.get("almuerzo_uf_dia"), 0.0)                # UF/día
INCENTIVO_UF = safe_float(param.get("incentivo_por_gps"), 0.0)         # UF/GPS
H_DIA = safe_float(param.get("horas_jornada"), 7.0)                    # 7
VEL = safe_float(param.get("velocidad_terrestre"), 80.0)               # 80
DIAS_SEM = int(safe_float(param.get("dias_semana"), 6))
SEMANAS = int(safe_float(param.get("semanas_proyecto"), 4))
DIAS_MAX = DIAS_SEM * SEMANAS
HH_MES = safe_float(param.get("hh_mes"), 180.0)                        # si no existe, default 180h/mes

# Externos + flete
PXQ_UF = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))
FLETE_UF = dict(zip(flete["ciudad"], flete["costo_flete"]))  # asumo UF; si es CLP, divide por UF aquí

# =========================
# 4. FUNCIONES AUXILIARES
# =========================
def base_tecnico(tecnico: str) -> str:
    return internos.loc[internos["tecnico"] == tecnico, "ciudad_base"].values[0]

def alpha_tecnico(tecnico: str) -> float:
    """
    alpha = HH_semana_proyecto / (6 dias * H_DIA)
    """
    hh_sem = safe_float(internos.loc[internos["tecnico"] == tecnico, "hh_semana_proyecto"].values[0], 0.0)
    denom = max(1e-9, DIAS_SEM * H_DIA)
    return hh_sem / denom

def horas_diarias(tecnico: str) -> float:
    return H_DIA * alpha_tecnico(tecnico)

def t_viaje(ciudad_origen: str, ciudad_destino: str, modo: str) -> float:
    if ciudad_origen == ciudad_destino:
        return 0.0
    if modo == "terrestre":
        return safe_float(km.loc[ciudad_origen, ciudad_destino], 0.0) / max(1e-9, VEL)
    # avión: viene como hora Excel (datetime.time) o float
    return time_to_hours(avion_time.loc[ciudad_origen, ciudad_destino])

def costo_viaje_uf(ciudad_origen: str, ciudad_destino: str, modo: str) -> float:
    """
    Retorna costo de viaje en UF.
    Terrestre: (km*precio_bencina + peajes) en CLP -> UF
    Avión: costo matriz (asumido CLP) -> UF
    """
    if ciudad_origen == ciudad_destino:
        return 0.0

    if modo == "terrestre":
        dist_km = safe_float(km.loc[ciudad_origen, ciudad_destino], 0.0)
        peaje = safe_float(peajes.loc[ciudad_origen, ciudad_destino], 0.0)
        clp = dist_km * PRECIO_BENCINA + peaje
        return clp / max(1e-9, UF)

    # avión
    clp = safe_float(avion_cost.loc[ciudad_origen, ciudad_destino], 0.0)
    return clp / max(1e-9, UF)

def dias_ciudad(ciudad: str, tecnico: str, modo: str, origen: str = None) -> int:
    """
    Días necesarios para terminar ciudad completa.
    Día 1: viaja en la mañana (origen->ciudad) y trabaja lo que alcance.
    Días siguientes: trabaja horas_diarias completas.
    """
    if origen is None:
        origen = base_tecnico(tecnico)

    tv = t_viaje(origen, ciudad, modo)
    hd = horas_diarias(tecnico)

    h_dia1 = max(0.0, hd - tv)
    rem = max(0.0, H[ciudad] - h_dia1)

    if rem <= 1e-9:
        return 1
    return 1 + int(math.ceil(rem / max(1e-9, hd)))

def costo_sueldo_proyecto_uf(tecnico: str) -> float:
    """
    sueldo interno = sueldo_UF/mes * (HH_proyecto / HH_mes)
    HH_proyecto = hh_semana_proyecto * semanas_proyecto
    """
    sueldo_mes = safe_float(internos.loc[internos["tecnico"] == tecnico, "sueldo_uf"].values[0], 0.0)
    hh_sem = safe_float(internos.loc[internos["tecnico"] == tecnico, "hh_semana_proyecto"].values[0], 0.0)
    hh_proy = hh_sem * SEMANAS
    return sueldo_mes * (hh_proy / max(1e-9, HH_MES))

def costo_interno_base_a_ciudad(ciudad: str, tecnico: str, modo: str) -> float:
    """
    Costo aproximado Fase 1: base->ciudad, terminar ciudad, costos agregados.
    Nota: Fase 2 modela secuencia real multi-ciudad.
    """
    base = base_tecnico(tecnico)
    dias = dias_ciudad(ciudad, tecnico, modo, origen=base)

    costo = 0.0

    # sueldo prorrateado por carga de días (aprox)
    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    costo += sueldo_proy * (dias / DIAS_MAX)

    # alojamiento (solo fuera de base)
    if ciudad != base:
        costo += dias * ALOJ_UF

    # almuerzo
    costo += dias * ALMU_UF

    # incentivo por GPS (UF)
    costo += INCENTIVO_UF * GPS_TOTAL[ciudad]

    # transporte base->ciudad (UF)
    costo += costo_viaje_uf(base, ciudad, modo)

    # flete: solo sale de Santiago hacia afuera en terrestre si interno base Santiago (lleva materiales)
    # - si base != Santiago -> siempre flete
    # - si base == Santiago:
    #    - terrestre: NO flete (lleva materiales)
    #    - avión: SÍ flete (materiales van por Chilexpress)
    if base != SANTIAGO or modo == "avion":
        costo += safe_float(FLETE_UF.get(ciudad, 0.0), 0.0)

    return costo

def costo_externo_ciudad(ciudad: str) -> float:
    return safe_float(PXQ_UF.get(ciudad, 0.0), 0.0) + safe_float(FLETE_UF.get(ciudad, 0.0), 0.0)

# =========================
# 5. FASE 1 – MILP (WARM START)
# =========================
def solve_phase1():
    m = pyo.ConcreteModel()

    m.C = pyo.Set(initialize=CIUDADES)
    m.T = pyo.Set(initialize=TECNICOS)
    m.M = pyo.Set(initialize=MODOS)

    # x[c,t,mo] = 1 si ciudad c la hace técnico t en modo mo (solo si interno)
    m.x = pyo.Var(m.C, m.T, m.M, domain=pyo.Binary)

    # y[c] = 1 si ciudad c es interna (Santiago se deja flexible)
    m.y = pyo.Var(m.C, domain=pyo.Binary)

    # objetivo
    def obj_rule(mm):
        cost = 0.0
        for c in mm.C:
            # internos
            cost += sum(mm.x[c, t, mo] * costo_interno_base_a_ciudad(c, t, mo) for t in mm.T for mo in mm.M)

            # externos
            # Warm start conservador: Santiago también se fuerza a uno (interno vs externo)
            cost += (1 - mm.y[c]) * costo_externo_ciudad(c)
        return cost

    m.OBJ = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

    # Link x <= y (si se asigna interno, entonces y=1)
    def link_xy(mm, c, t, mo):
        return mm.x[c, t, mo] <= mm.y[c]

    m.LINK = pyo.Constraint(m.C, m.T, m.M, rule=link_xy)

    # Asignación única para ciudades != Santiago (solo un técnico interno o externo)
    def unica_ciudad(mm, c):
        if c == SANTIAGO:
            return pyo.Constraint.Skip
        return sum(mm.x[c, t, mo] for t in mm.T for mo in mm.M) == mm.y[c]

    m.UNICA = pyo.Constraint(m.C, rule=unica_ciudad)

    # En ciudades != Santiago: no más de 1 técnico interno
    def one_tech_per_city(mm, c):
        if c == SANTIAGO:
            return pyo.Constraint.Skip
        return sum(mm.x[c, t, mo] for t in mm.T for mo in mm.M) <= 1

    m.ONE = pyo.Constraint(m.C, rule=one_tech_per_city)

    # Santiago: permitir hasta 5 internos en warm-start (si y[SCL]=1)
    def santiago_cap(mm):
        return sum(mm.x[SANTIAGO, t, mo] for t in mm.T for mo in mm.M) <= 5

    m.SCLCAP = pyo.Constraint(rule=santiago_cap)

    # Capacidad por técnico (días) aproximada base->ciudad
    def capacidad(mm, t):
        return sum(dias_ciudad(c, t, mo, origen=base_tecnico(t)) * mm.x[c, t, mo] for c in mm.C for mo in mm.M) <= DIAS_MAX

    m.CAP = pyo.Constraint(m.T, rule=capacidad)

    # Resolver
    solver = pyo.SolverFactory(SOLVER)
    res = solver.solve(m)

    # Extraer solución
    assign = {}
    mode = {}
    y_val = {}

    for c in CIUDADES:
        y_val[c] = int(pyo.value(m.y[c]) > 0.5)

    for c in CIUDADES:
        for t in TECNICOS:
            for mo in MODOS:
                if pyo.value(m.x[c, t, mo]) > 0.5:
                    assign[(t, c)] = 1
                    mode[(t, c)] = mo

    # Guardar salida fase1
    rows = []
    for (t, c), _ in assign.items():
        mo = mode[(t, c)]
        rows.append([c, t, mo, costo_interno_base_a_ciudad(c, t, mo), dias_ciudad(c, t, mo, origen=base_tecnico(t))])

    df = pd.DataFrame(rows, columns=["ciudad", "tecnico", "modo", "costo_aprox_fase1_uf", "dias_aprox_fase1"])
    df.to_excel(os.path.join(OUTPUTS_DIR, "resultado_optimizacion_gps_fase1.xlsx"), index=False)

    return {"I": y_val, "assign": assign, "mode": mode}

# =========================
# 6. FASE 2 – MEJORA GLOBAL (2B)
# =========================
def build_initial_solution(ws):
    """
    city_type[c]: "interno"/"externo"/"mixto_scl"
    tech_cities[t]: lista de ciudades internas (excluye Santiago)
    """
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
    """
    Simulación día a día (simple y robusta):
    - Parte durmiendo en base.
    - Para cada ciudad: viaja en la mañana desde donde durmió.
    - Instala lo que alcance, y se queda hasta terminar.
    - Alojamiento: noche por presencia fuera de base al cierre del día.
    - Permite "viajar al cierre" solo si sobra tiempo (implementación simple).
      (Por defecto: NO hace evening-hop para no duplicar viajes. Se puede activar después.)
    """
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

    # Sueldo por día
    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / DIAS_MAX

    # Pendiente por ciudad (horas)
    pending_h = {c: H[c] for c in cities_list}

    # Regla flete por ciudad interna (si corresponde) en fase 2:
    # - base Santiago: si el primer movimiento a esa ciudad es terrestre -> lleva materiales -> no flete
    # - base Santiago: si llega por avión -> flete
    # - base no Santiago: siempre flete
    # Simplificación: cobramos flete una vez por ciudad (si aplica) cuando "entra" a ciudad
    def flete_aplica(ciudad, modo_llegada):
        if base != SANTIAGO:
            return True
        if modo_llegada == "avion":
            return True
        return False  # base Santiago + terrestre -> lleva

    for c in cities_list:
        if pending_h[c] <= 1e-9:
            continue

        # Elegir modo más barato para el tramo sleep_city -> c
        road_cost = costo_viaje_uf(sleep_city, c, "terrestre")
        air_cost = costo_viaje_uf(sleep_city, c, "avion")

        if air_cost < road_cost:
            modo_in = "avion"
        else:
            modo_in = "terrestre"

        tv = t_viaje(sleep_city, c, modo_in)
        cv = costo_viaje_uf(sleep_city, c, modo_in)

        if day > DIAS_MAX:
            break

        # Día llegada (mañana)
        time_left = max(0.0, hd - tv)

        cost["travel_uf"] += cv
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia

        # flete por ciudad (si aplica)
        if flete_aplica(c, modo_in):
            cost["flete_uf"] += safe_float(FLETE_UF.get(c, 0.0), 0.0)

        installed = min(pending_h[c], time_left)
        pending_h[c] -= installed
        gps_inst = installed / 0.75

        cost["inc_uf"] += INCENTIVO_UF * gps_inst

        # duerme en ciudad c
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

        # Días completos hasta terminar ciudad
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

    # factibilidad: no exceder DIAS_MAX
    feasible = (day - 1) <= DIAS_MAX
    return plan, cost, feasible

def total_cost_solution(city_type, tech_cities):
    total = 0.0
    details = []

    # internos
    for t, clist in tech_cities.items():
        if not clist:
            continue
        plan, cst, feas = simulate_tech_schedule(t, clist)
        if not feas:
            return 1e18, []  # infeasible duro
        tot_t = sum(cst.values())
        total += tot_t
        details.append(("INTERNAL", t, tot_t, cst))

    # externos (por ciudad)
    for c in CIUDADES:
        if c == SANTIAGO:
            continue
        if city_type.get(c) == "externo":
            total += costo_externo_ciudad(c)
            details.append(("EXTERNAL", c, costo_externo_ciudad(c), {"pxq_flete_uf": costo_externo_ciudad(c)}))

    return total, details

def improve_solution(city_type, tech_cities, iters=300, seed=42):
    """
    Mejora global:
    - flip interno <-> externo para una ciudad
    - reasignar ciudad interna entre técnicos
    Acepta solo si mejora costo total y es factible.
    """
    best_ct = deepcopy(city_type)
    best_tc = deepcopy(tech_cities)
    best_cost, _ = total_cost_solution(best_ct, best_tc)

    rng = np.random.default_rng(seed)

    cities_no_scl = [c for c in CIUDADES if c != SANTIAGO]

    for _ in range(iters):
        ct2 = deepcopy(best_ct)
        tc2 = deepcopy(best_tc)

        move_type = rng.integers(0, 2)  # 0 flip, 1 reassign

        if move_type == 0:
            c = rng.choice(cities_no_scl)

            if ct2.get(c) == "interno":
                # pasa a externo
                ct2[c] = "externo"
                for t in TECNICOS:
                    if c in tc2[t]:
                        tc2[t].remove(c)
            else:
                # pasa a interno: asignar al técnico que quede factible y mínimo costo
                ct2[c] = "interno"
                best_t = None
                best_cost_t = 1e18

                for t in TECNICOS:
                    trial = tc2[t] + [c]
                    plan, cst, feas = simulate_tech_schedule(t, trial)
                    if not feas:
                        continue
                    cost_t = sum(cst.values())
                    if cost_t < best_cost_t:
                        best_cost_t = cost_t
                        best_t = t

                if best_t is None:
                    continue
                tc2[best_t].append(c)

        else:
            # reasignar ciudad interna
            donors = [t for t in TECNICOS if len(tc2[t]) > 0]
            if not donors:
                continue

            t_from = rng.choice(donors)
            c = rng.choice(tc2[t_from])
            t_to = rng.choice([t for t in TECNICOS if t != t_from])

            tc2[t_from].remove(c)
            tc2[t_to].append(c)

        new_cost, _ = total_cost_solution(ct2, tc2)
        if new_cost + 1e-6 < best_cost:
            best_cost = new_cost
            best_ct = ct2
            best_tc = tc2

    return best_ct, best_tc, best_cost

# =========================
# 7. RUN ALL + EXPORT
# =========================
def run_all():
    ws = solve_phase1()
    city_type, tech_cities = build_initial_solution(ws)

    # Mejora global 2B
    city_type2, tech_cities2, best_cost = improve_solution(city_type, tech_cities, iters=300)

    plan_rows = []
    cost_rows = []

    # Internos: secuencia diaria + costos
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

    # Externos: 1 por ciudad hasta terminar (costos agregados por ciudad)
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
                "flete_uf": safe_float(FLETE_UF.get(c, 0.0), 0.0),
                "total_uf": costo_externo_ciudad(c),
            })

    df_plan = pd.DataFrame(plan_rows).sort_values(["tecnico", "dia"])
    df_cost = pd.DataFrame(cost_rows).sort_values(["tipo", "total_uf"], ascending=[True, False])
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
