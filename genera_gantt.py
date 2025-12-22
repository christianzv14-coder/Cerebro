import math
import pandas as pd
import numpy as np
import plotly.express as px

# =========================
# CONFIG
# =========================
FILE_RESULTADO = "resultado_optimizacion_gps_v6.xlsx"
FILE_DEMANDA = "demanda_ciudades.xlsx"  # si no está dentro del resultado, usa este

HORAS_DIA = 7.0
DIAS_MAX = 24  # 4 semanas * 6 días

# =========================
# HELPERS
# =========================
def norm_col(df):
    df.columns = [str(c).strip() for c in df.columns]
    return df

def find_sheet_with_columns(xls, required_cols):
    for sh in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sh)
        df = norm_col(df)
        cols = set(df.columns)
        if all(c in cols for c in required_cols):
            return sh, df
    return None, None

def ceil_div(a, b):
    return int(math.ceil(a / b))

# =========================
# CARGA
# =========================
xls = pd.ExcelFile(FILE_RESULTADO)

# 1) Buscar plan diario internos
req_plan = ["tecnico", "dia", "ciudad_trabajo", "horas_instal"]
sh_plan, df_plan = find_sheet_with_columns(xls, req_plan)
if df_plan is None:
    raise ValueError(
        f"No encontré una hoja con columnas {req_plan} en {FILE_RESULTADO}. "
        "Revisa nombres de columnas/hojas."
    )

df_plan = df_plan.copy()
df_plan["tecnico"] = df_plan["tecnico"].astype(str).str.strip()
df_plan["ciudad_trabajo"] = df_plan["ciudad_trabajo"].astype(str).str.strip()
df_plan["dia"] = pd.to_numeric(df_plan["dia"], errors="coerce").fillna(0).astype(int)
df_plan["horas_instal"] = pd.to_numeric(df_plan["horas_instal"], errors="coerce").fillna(0.0)

# Filtrar filas sin ciudad o sin técnico
df_plan = df_plan[(df_plan["tecnico"] != "") & (df_plan["ciudad_trabajo"] != "")]

# 2) Buscar “tipo ciudad final” (interno/externo)
# Intentamos primero dentro del mismo excel
req_tipo = ["ciudad", "tipo_final"]
sh_tipo, df_tipo = find_sheet_with_columns(xls, req_tipo)

if df_tipo is None:
    # Si no existe en el resultado, asumimos que ciudades NO presentes en plan interno son externas,
    # pero para eso necesitamos la lista completa de ciudades desde demanda.
    demanda = pd.read_excel(FILE_DEMANDA)
    demanda = norm_col(demanda)
    demanda["ciudad"] = demanda["ciudad"].astype(str).str.strip()
    cities_all = demanda["ciudad"].tolist()

    cities_internas = set(df_plan["ciudad_trabajo"].unique())
    df_tipo = pd.DataFrame({
        "ciudad": cities_all,
        "tipo_final": ["interno" if c in cities_internas else "externo" for c in cities_all]
    })
else:
    df_tipo = df_tipo.copy()
    df_tipo["ciudad"] = df_tipo["ciudad"].astype(str).str.strip()
    df_tipo["tipo_final"] = df_tipo["tipo_final"].astype(str).str.strip().str.lower()

# 3) Cargar demanda para horas por ciudad (para construir externos)
demanda = None
try:
    demanda = pd.read_excel(xls, sheet_name="demanda_ciudades")
    demanda = norm_col(demanda)
except Exception:
    demanda = pd.read_excel(FILE_DEMANDA)
    demanda = norm_col(demanda)

demanda["ciudad"] = demanda["ciudad"].astype(str).str.strip()
for c in ["vehiculos_1gps", "vehiculos_2gps"]:
    demanda[c] = pd.to_numeric(demanda[c], errors="coerce").fillna(0)

demanda["gps_total"] = demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]
demanda["horas"] = 0.75 * demanda["gps_total"]

H_city = dict(zip(demanda["ciudad"], demanda["horas"]))

# =========================
# GANTT INTERNOS
# =========================
df_internal = df_plan[df_plan["horas_instal"] > 0].copy()

# Agrupación por tramos: si hay huecos grandes y quieres separar tramos, se puede.
# Por ahora: un bloque por (tecnico, ciudad) usando min y max del día.
gantt_int = (
    df_internal.groupby(["tecnico", "ciudad_trabajo"], as_index=False)
    .agg(start_day=("dia", "min"), end_day=("dia", "max"))
)
gantt_int["finish_day"] = gantt_int["end_day"] + 1
gantt_int["resource"] = gantt_int["tecnico"]
gantt_int["task"] = gantt_int["ciudad_trabajo"]
gantt_int["tipo"] = "interno"

# =========================
# GANTT EXTERNOS
# =========================
externas = df_tipo[df_tipo["tipo_final"].str.contains("extern")]["ciudad"].tolist()

rows_ext = []
for c in externas:
    h = float(H_city.get(c, 0.0))
    if h <= 1e-9:
        continue
    dias = ceil_div(h, HORAS_DIA)
    start = 1
    finish = min(DIAS_MAX + 1, start + dias)  # cap por horizonte
    rows_ext.append({
        "resource": f"EXTERNO - {c}",
        "task": c,
        "start_day": start,
        "finish_day": finish,
        "tipo": "externo"
    })

gantt_ext = pd.DataFrame(rows_ext)

# =========================
# UNIFICAR Y EXPORTAR TABLA
# =========================
gantt_all = pd.concat([
    gantt_int[["resource", "task", "start_day", "finish_day", "tipo"]],
    gantt_ext[["resource", "task", "start_day", "finish_day", "tipo"]] if not gantt_ext.empty else pd.DataFrame()
], ignore_index=True)

# Crear fechas ficticias para Plotly (día 1 = 2026-01-01 por ejemplo)
base_date = pd.Timestamp("2026-01-01")
gantt_all["Start"] = base_date + pd.to_timedelta(gantt_all["start_day"] - 1, unit="D")
gantt_all["Finish"] = base_date + pd.to_timedelta(gantt_all["finish_day"] - 1, unit="D")

# Export tabla base
gantt_all.to_excel("tabla_gantt_base.xlsx", index=False)

# =========================
# 1) GANTT OPERACIÓN (internos)
# =========================
fig1 = px.timeline(
    gantt_int.assign(
        Start=base_date + pd.to_timedelta(gantt_int["start_day"] - 1, unit="D"),
        Finish=base_date + pd.to_timedelta(gantt_int["finish_day"] - 1, unit="D")
    ),
    x_start="Start",
    x_end="Finish",
    y="resource",
    color="task",
    title="Carta Gantt Operación – Internos (por técnico)"
)
fig1.update_yaxes(autorange="reversed")
fig1.write_html("gantt_operacion_internos.html")

# =========================
# 2) GANTT CLIENTE (ciudades, interno vs externo)
# =========================
fig2 = px.timeline(
    gantt_all,
    x_start="Start",
    x_end="Finish",
    y="task",
    color="tipo",
    title="Carta Gantt Cliente – Instalación por ciudad (interno vs externo)"
)
fig2.update_yaxes(autorange="reversed")
fig2.write_html("gantt_cliente_ciudades.html")

print("[OK] Generé:")
print(" - tabla_gantt_base.xlsx")
print(" - gantt_operacion_internos.html")
print(" - gantt_cliente_ciudades.html")
print(f"[INFO] Plan interno desde hoja: {sh_plan}")
print(f"[INFO] Tipo ciudad desde hoja: {sh_tipo if sh_tipo else 'inferido'}")
