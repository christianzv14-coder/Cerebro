# modelo_optimizacion_gps_chile_v3_materiales.py
# Heurística (greedy + mejora aleatoria) + simulación día a día
# FIX 1: hh_semana_proyecto interpretado como FTE si <= 1.5 (ej: 0.5 = 50% jornada)
# FIX 2: la simulación valida que TODAS las horas de instalación queden completadas (no solo días <= DIAS_MAX)
# FIX 3: costos de materiales/kits incluidos (UF) en el total
#
# Requiere: pandas, numpy, openpyxl
# Inputs en ./data/ (o cambia PATH)
# Output: outputs/resultado_optimizacion_gps_v3.xlsx

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
# 1. UTILIDADES
# =========================
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
        raise ValueError(f"Matriz {name} no cubre todas las ciudades. Faltan filas={missing_rows}, cols={missing_cols}")

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

PRECIO_BENCINA_UF_KM = safe_float(param.get("precio_bencina"), 0.03)  # UF/km
ALOJ_UF = safe_float(param.get("alojamiento_uf_noche"), 1.1)
ALMU_UF = safe_float(param.get("almuerzo_uf_dia"), 0.5)
INCENTIVO_UF = safe_float(param.get("incentivo_por_gps"), 1.12)
H_DIA = safe_float(param.get("horas_jornada"), 7.0)
VEL = safe_float(param.get("velocidad_terrestre"), 80.0)
TIEMPO_INST_GPS_H = safe_float(param.get("tiempo_instalacion_gps"), 0.75)

DIAS_SEM = int(safe_float(param.get("dias_semana"), 6))
SEMANAS = int(safe_float(param.get("semanas_proyecto"), 4))
DIAS_MAX = DIAS_SEM * SEMANAS
HH_MES = safe_float(param.get("hh_mes"), 180.0)

demanda["gps_total"] = demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]
demanda["horas"] = TIEMPO_INST_GPS_H * demanda["gps_total"]

H = dict(zip(demanda["ciudad"], demanda["horas"]))
GPS_TOTAL = dict(zip(demanda["ciudad"], demanda["gps_total"]))
VEH1 = dict(zip(demanda["ciudad"], demanda["vehiculos_1gps"]))
VEH2 = dict(zip(demanda["ciudad"], demanda["vehiculos_2gps"]))

# Materiales: se asume que 'costo' en materiales.xlsx viene en UF
KIT1 = safe_float(kits.loc[kits["tipo_kit"] == "1_GPS", "costo"].values[0], 0.0)
KIT2 = safe_float(kits.loc[kits["tipo_kit"] == "2_GPS", "costo"].values[0], 0.0)
MATERIAL_UF = {c: safe_float(VEH1.get(c, 0), 0) * KIT1 + safe_float(VEH2.get(c, 0), 0) * KIT2 for c in CIUDADES}

pxq["ciudad"] = pxq["ciudad"].apply(norm_city)
flete["ciudad"] = flete["ciudad"].apply(norm_city)

# PXQ es UF por GPS (confirmado por ti)
PXQ_UF_POR_GPS = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))  # UF por GPS
# Flete ya viene en UF
FLETE_UF = dict(zip(flete["ciudad"], flete["costo_flete"]))     # UF

# =========================
# 5. FUNCIONES
# =========================
def base_tecnico(tecnico: str) -> str:
    return internos.loc[internos["tecnico"] == tecnico, "ciudad_base"].values[0]

def hh_semana(tecnico: str) -> float:
    v = safe_float(internos.loc[internos["tecnico"] == tecnico, "hh_semana_proyecto"].values[0], 0.0)
    # FIX: si viene como FTE (0-1), convertir a horas/semana reales
    if v <= 1.5:
        return v * (DIAS_SEM * H_DIA)
    return v

def alpha_tecnico(tecnico: str) -> float:
    return hh_semana(tecnico) / max(1e-9, DIAS_SEM * H_DIA)

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
        peaje_uf = safe_float(peajes.loc[ciudad_origen, ciudad_destino], 0.0)
        return dist_km * PRECIO_BENCINA_UF_KM + peaje_uf
    return safe_float(avion_cost.loc[ciudad_origen, ciudad_destino], 0.0)

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
    pxq_total = safe_float(PXQ_UF_POR_GPS.get(ciudad, 0.0), 0.0) * safe_float(GPS_TOTAL.get(ciudad, 0.0), 0.0)
    return pxq_total + safe_float(FLETE_UF.get(ciudad, 0.0), 0.0) + safe_float(MATERIAL_UF.get(ciudad, 0.0), 0.0)

def costo_interno_base_a_ciudad(ciudad: str, tecnico: str, modo: str) -> float:
    base = base_tecnico(tecnico)
    dias = dias_ciudad(ciudad, tecnico, modo, origen=base)

    costo = 0.0
    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    costo += sueldo_proy * (dias / DIAS_MAX)

    if ciudad != base:
        costo += dias * ALOJ_UF

    costo += dias * ALMU_UF
    costo += INCENTIVO_UF * GPS_TOTAL[ciudad]
    costo += costo_viaje_uf(base, ciudad, modo)

    # flete: solo NO aplica si base Santiago y llega terrestre
    if base != SANTIAGO or modo == "avion":
        costo += safe_float(FLETE_UF.get(ciudad, 0.0), 0.0)

    # materiales siempre
    costo += safe_float(MATERIAL_UF.get(ciudad, 0.0), 0.0)

    return costo

# =========================
# 6. SIMULACIÓN (día a día) + VALIDACIÓN COMPLETITUD
# =========================
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
        "material_uf": 0.0,
    }

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1e-9, DIAS_MAX)
    pending_h = {c: H[c] for c in cities_list}
    added_material = set()

    def flete_aplica(ciudad, modo_llegada):
        if base != SANTIAGO:
            return True
        return modo_llegada == "avion"

    for c in cities_list:
        if day > DIAS_MAX:
            break

        if pending_h[c] <= 1e-9:
            if c not in added_material:
                cost["material_uf"] += safe_float(MATERIAL_UF.get(c, 0.0), 0.0)
                added_material.add(c)
            continue

        road_cost = costo_viaje_uf(sleep_city, c, "terrestre")
        air_cost = costo_viaje_uf(sleep_city, c, "avion")
        modo_in = "avion" if air_cost < road_cost else "terrestre"

        tv = t_viaje(sleep_city, c, modo_in)
        cv = costo_viaje_uf(sleep_city, c, modo_in)
        time_left = max(0.0, hd - tv)

        cost["travel_uf"] += cv
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia

        flete_day = safe_float(FLETE_UF.get(c, 0.0), 0.0) if flete_aplica(c, modo_in) else 0.0
        cost["flete_uf"] += flete_day

        mat_day = 0.0
        if c not in added_material:
            mat_day = safe_float(MATERIAL_UF.get(c, 0.0), 0.0)
            cost["material_uf"] += mat_day
            added_material.add(c)

        installed = min(pending_h[c], time_left)
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
            "material_uf": mat_day,
        })
        day += 1

        while pending_h[c] > 1e-9 and day <= DIAS_MAX:
            installed = min(pending_h[c], hd)
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
            })
            day += 1

    # FIX: factibilidad exige completar TODAS las horas
    complete = all(hh <= 1e-6 for hh in pending_h.values())
    feasible = (day - 1) <= DIAS_MAX and complete
    return plan, cost, feasible

def total_all_external():
    return sum(costo_externo_ciudad(c) for c in CIUDADES)

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
            # Santiago como mixto: solo materiales por defecto
            total += safe_float(MATERIAL_UF.get(c, 0.0), 0.0)
            continue
        if city_type.get(c) == "externo":
            total += costo_externo_ciudad(c)
    return total

# =========================
# 7. INICIAL (GREEDY) + MEJORA
# =========================
def greedy_initial():
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
            for mo in MODOS:
                base = base_tecnico(t)
                dias = dias_ciudad(c, t, mo, origen=base)
                if dias > DIAS_MAX:
                    continue
                intc = costo_interno_base_a_ciudad(c, t, mo)
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

def improve_solution(city_type, tech_cities, iters=2000, seed=7):
    best_ct = deepcopy(city_type)
    best_tc = deepcopy(tech_cities)
    best_cost = total_cost_solution(best_ct, best_tc)

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
                best_total = 1e18
                for t in TECNICOS:
                    if c in tc2[t]:
                        continue
                    trial = tc2[t] + [c]
                    _, cst, feas = simulate_tech_schedule(t, trial)
                    if not feas:
                        continue
                    total = sum(cst.values())
                    if total < best_total:
                        best_total = total
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

        new_cost = total_cost_solution(ct2, tc2)
        if new_cost + 1e-6 < best_cost:
            best_cost = new_cost
            best_ct = ct2
            best_tc = tc2

    return best_ct, best_tc, best_cost

# =========================
# 8. RUN + EXPORT EXCEL
# =========================
def run_all():
    ct0, tc0 = greedy_initial()
    ct, tc, best_cost = improve_solution(ct0, tc0)

    plan_rows = []
    tech_cost_rows = []
    city_resp = {}

    for t, clist in tc.items():
        if not clist:
            continue
        for c in clist:
            city_resp[c] = t

        plan, cst, feas = simulate_tech_schedule(t, clist)
        if not feas:
            raise RuntimeError(f"Solución infeasible para técnico {t}. Revisa carga/HH.")

        plan_rows.extend(plan)
        tech_cost_rows.append({
            "responsable": t,
            "tipo": "INTERNO",
            **cst,
            "total_uf": sum(cst.values()),
            "ciudades": ", ".join(clist)
        })

    df_plan = pd.DataFrame(plan_rows)
    if not df_plan.empty:
        df_plan = df_plan.sort_values(["tecnico", "dia"])

    city_rows = []
    if not df_plan.empty:
        agg = df_plan.groupby("ciudad_trabajo")[[
            "viaje_uf","aloj_uf","alm_uf","inc_uf","sueldo_uf","flete_uf","material_uf","horas_instal","gps_inst"
        ]].sum().reset_index()
        agg_map = {r["ciudad_trabajo"]: r for _, r in agg.iterrows()}
    else:
        agg_map = {}

    for c in CIUDADES:
        if c == SANTIAGO:
            city_rows.append({
                "ciudad": c, "tipo_final": "mixto_scl", "responsable": None,
                "viaje_uf": 0.0, "aloj_uf": 0.0, "alm_uf": 0.0, "inc_uf": 0.0, "sueldo_uf": 0.0, "flete_uf": 0.0,
                "pxq_total_uf": 0.0, "material_uf": safe_float(MATERIAL_UF.get(c, 0.0), 0.0),
                "total_uf": safe_float(MATERIAL_UF.get(c, 0.0), 0.0),
                "gps_total": safe_float(GPS_TOTAL.get(c, 0.0), 0.0),
                "horas_instal_total": safe_float(H.get(c, 0.0), 0.0),
            })
            continue

        if c in city_resp:
            r = agg_map.get(c)
            row = {
                "ciudad": c, "tipo_final": "interno", "responsable": city_resp[c],
                "viaje_uf": float(r["viaje_uf"]), "aloj_uf": float(r["aloj_uf"]), "alm_uf": float(r["alm_uf"]),
                "inc_uf": float(r["inc_uf"]), "sueldo_uf": float(r["sueldo_uf"]), "flete_uf": float(r["flete_uf"]),
                "pxq_total_uf": 0.0, "material_uf": float(r["material_uf"]),
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
            pxq_total = safe_float(PXQ_UF_POR_GPS.get(c, 0.0), 0.0) * safe_float(GPS_TOTAL.get(c, 0.0), 0.0)
            row = {
                "ciudad": c, "tipo_final": "externo", "responsable": c,
                "viaje_uf": 0.0, "aloj_uf": 0.0, "alm_uf": 0.0, "inc_uf": 0.0, "sueldo_uf": 0.0,
                "flete_uf": safe_float(FLETE_UF.get(c, 0.0), 0.0),
                "pxq_total_uf": pxq_total,
                "material_uf": safe_float(MATERIAL_UF.get(c, 0.0), 0.0),
                "total_uf": costo_externo_ciudad(c),
                "gps_total": safe_float(GPS_TOTAL.get(c, 0.0), 0.0),
                "horas_instal_total": safe_float(H.get(c, 0.0), 0.0),
            }
            city_rows.append(row)

    df_city = pd.DataFrame(city_rows).sort_values("total_uf", ascending=False)
    df_tech = pd.DataFrame(tech_cost_rows).sort_values("total_uf", ascending=False)

    baseline = total_all_external()
    resumen = {
        "baseline_all_external_uf": baseline,
        "final_total_uf": df_city["total_uf"].sum(),
        "savings_uf": baseline - df_city["total_uf"].sum(),
        "n_internal_cities": int((df_city["tipo_final"] == "interno").sum()),
        "n_external_cities": int((df_city["tipo_final"] == "externo").sum()),
    }
    comp = df_city[[
        "viaje_uf","aloj_uf","alm_uf","inc_uf","sueldo_uf","flete_uf","pxq_total_uf","material_uf","total_uf"
    ]].sum().to_dict()
    df_resumen = pd.DataFrame([resumen | {f"sum_{k}": v for k, v in comp.items()}])

    df_demand = demanda.copy()
    df_demand["material_uf"] = df_demand["ciudad"].map(MATERIAL_UF)
    df_demand["pxq_uf_gps"] = df_demand["ciudad"].map(PXQ_UF_POR_GPS)
    df_demand["flete_uf"] = df_demand["ciudad"].map(FLETE_UF)

    df_params = pd.DataFrame([{"parametro": k, "valor": v} for k, v in param.items()])

    out_path = os.path.join(OUTPUTS_DIR, "resultado_optimizacion_gps_v3.xlsx")
    with pd.ExcelWriter(out_path) as w:
        df_resumen.to_excel(w, index=False, sheet_name="Resumen_Total")
        df_city.to_excel(w, index=False, sheet_name="Costos_por_Ciudad")
        df_tech.to_excel(w, index=False, sheet_name="Costos_por_Tecnico")
        df_plan.to_excel(w, index=False, sheet_name="Plan_Diario")
        df_demand.to_excel(w, index=False, sheet_name="Demanda_y_Materiales")
        df_params.to_excel(w, index=False, sheet_name="Parametros")

    print("[OK] ->", out_path)
    print("[OK] Total final (UF):", round(df_city["total_uf"].sum(), 4))
    print("[OK] Baseline all external (UF):", round(baseline, 4))
    print("[OK] Ahorro (UF):", round(baseline - df_city["total_uf"].sum(), 4))

if __name__ == "__main__":
    run_all()
