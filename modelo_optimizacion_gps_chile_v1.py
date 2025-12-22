# genera_gantt.py
# Genera carta Gantt a partir del último Excel .xlsx en ./outputs (auto-detect)
# Outputs:
# - outputs/tabla_gantt_base.xlsx (tabla base para Gantt)
# - outputs/gantt_operacion_internos.html (Gantt por técnico)
# - outputs/gantt_cliente_ciudades.html (Gantt por ciudad)
#
# Requiere: pandas, numpy, openpyxl, plotly

import os
import glob
import math
from datetime import datetime

import numpy as np
import pandas as pd

try:
    import plotly.express as px
except ImportError as e:
    raise ImportError("Falta plotly. Instala con: pip install plotly") from e


# =========================
# 0) CONFIG
# =========================
OUTPUTS_DIR = "outputs"

# Columnas esperadas en plan diario (pueden venir de tu modelo)
COL_TECH = "tecnico"
COL_DAY = "dia"
COL_CITY = "ciudad_trabajo"
COL_HOURS = "horas_instal"
COL_SLEEP = "duerme_en"

# Si tu plan trae un modo de viaje, se usa como info
COL_MODE = "viaje_modo_manana"
COL_TRAVEL_H = "viaje_h_manana"

# Calendario (si no quieres fechas reales, se queda como "Día 1..N")
USE_REAL_DATES = False
PROJECT_START_DATE = "2025-01-01"  # usado solo si USE_REAL_DATES=True


# =========================
# 1) HELPERS
# =========================
def latest_xlsx_in_outputs(outputs_dir: str) -> str:
    files = glob.glob(os.path.join(outputs_dir, "*.xlsx"))
    if not files:
        raise FileNotFoundError(f"No se encontraron archivos .xlsx en la carpeta '{outputs_dir}'.")
    return max(files, key=os.path.getmtime)

def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    # normaliza headers por si vienen con tildes o espacios
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def find_sheet_with_columns(xls: pd.ExcelFile, required_cols: list[str]) -> str | None:
    for sh in xls.sheet_names:
        df = normalize_cols(pd.read_excel(xls, sheet_name=sh, nrows=5))
        if all(c in df.columns for c in required_cols):
            return sh
    return None

def to_int_day(x) -> int:
    try:
        return int(float(x))
    except Exception:
        return 0

def safe_float(x, default=0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, float) and np.isnan(x):
            return default
        return float(x)
    except Exception:
        return default

def compute_end_day(start_day: int, duration_days: int) -> int:
    return start_day + max(1, duration_days) - 1

def maybe_add_dates(df: pd.DataFrame) -> pd.DataFrame:
    if not USE_REAL_DATES:
        df["Inicio"] = df["Inicio_dia"].apply(lambda d: f"Día {d}")
        df["Fin"] = df["Fin_dia"].apply(lambda d: f"Día {d}")
        return df

    start_dt = pd.to_datetime(PROJECT_START_DATE)
    df["Inicio"] = df["Inicio_dia"].apply(lambda d: (start_dt + pd.Timedelta(days=d - 1)).date().isoformat())
    df["Fin"] = df["Fin_dia"].apply(lambda d: (start_dt + pd.Timedelta(days=d - 1)).date().isoformat())
    return df


# =========================
# 2) CARGA: ÚLTIMO XLSX
# =========================
file_resultado = latest_xlsx_in_outputs(OUTPUTS_DIR)
print(f"[INFO] Usando archivo de resultado: {file_resultado}")

xls = pd.ExcelFile(file_resultado)

# Buscamos una hoja "Plan_Diario" o equivalente
required = [COL_TECH, COL_DAY, COL_CITY]
sheet_plan = None
if "Plan_Diario" in xls.sheet_names:
    sheet_plan = "Plan_Diario"
else:
    sheet_plan = find_sheet_with_columns(xls, required)

if sheet_plan is None:
    raise ValueError(
        "No encontré una hoja con columnas mínimas para plan diario.\n"
        f"Busqué columnas: {required}\n"
        f"Hojas disponibles: {xls.sheet_names}\n"
        "Solución: asegúrate de exportar una hoja con 'tecnico', 'dia', 'ciudad_trabajo'."
    )

df_plan = normalize_cols(pd.read_excel(xls, sheet_name=sheet_plan))
print(f"[INFO] Hoja usada para plan: {sheet_plan} | filas: {len(df_plan)}")

# Validación mínima
for c in required:
    if c not in df_plan.columns:
        raise ValueError(f"Falta columna '{c}' en hoja {sheet_plan}. Columnas: {list(df_plan.columns)}")

# Limpieza
df_plan[COL_TECH] = df_plan[COL_TECH].astype(str).str.strip()
df_plan[COL_CITY] = df_plan[COL_CITY].astype(str).str.strip()
df_plan[COL_DAY] = df_plan[COL_DAY].apply(to_int_day)

if COL_HOURS in df_plan.columns:
    df_plan[COL_HOURS] = df_plan[COL_HOURS].apply(safe_float)
else:
    df_plan[COL_HOURS] = 0.0

if COL_SLEEP not in df_plan.columns:
    df_plan[COL_SLEEP] = ""

if COL_MODE not in df_plan.columns:
    df_plan[COL_MODE] = ""

if COL_TRAVEL_H not in df_plan.columns:
    df_plan[COL_TRAVEL_H] = 0.0
else:
    df_plan[COL_TRAVEL_H] = df_plan[COL_TRAVEL_H].apply(safe_float)

# Si está vacío, igual exportamos estructura
if df_plan.empty:
    print("[WARN] Plan diario vacío. Exporto plantillas vacías.")
    gantt_base = pd.DataFrame(columns=[
        "Responsable", "Ciudad", "Inicio_dia", "Fin_dia", "Duracion_dias",
        "Horas_instal_total", "GPS_inst_total", "Duerme_en_fin",
        "Inicio", "Fin"
    ])
else:
    # =========================
    # 3) TABLA BASE PARA GANTT
    #    Bloques consecutivos por técnico en una ciudad
    # =========================
    df_plan = df_plan.sort_values([COL_TECH, COL_DAY]).reset_index(drop=True)

    blocks = []
    for tech, g in df_plan.groupby(COL_TECH, sort=False):
        g = g.sort_values(COL_DAY).reset_index(drop=True)

        current_city = None
        start_day = None
        end_day = None
        sum_hours = 0.0

        # Si no tienes gps_inst, aproximamos por horas/0.75
        for i in range(len(g)):
            day_i = int(g.loc[i, COL_DAY])
            city_i = str(g.loc[i, COL_CITY])

            hours_i = float(g.loc[i, COL_HOURS]) if COL_HOURS in g.columns else 0.0

            # primer registro
            if current_city is None:
                current_city = city_i
                start_day = day_i
                end_day = day_i
                sum_hours = hours_i
                continue

            # es consecutivo y misma ciudad -> acumula
            if city_i == current_city and day_i == end_day + 1:
                end_day = day_i
                sum_hours += hours_i
            else:
                duration = (end_day - start_day + 1)
                blocks.append({
                    "Responsable": tech,
                    "Ciudad": current_city,
                    "Inicio_dia": int(start_day),
                    "Fin_dia": int(end_day),
                    "Duracion_dias": int(duration),
                    "Horas_instal_total": float(sum_hours),
                    "GPS_inst_total": float(sum_hours / 0.75) if sum_hours > 0 else 0.0,
                    "Duerme_en_fin": str(g.loc[i-1, COL_SLEEP]) if COL_SLEEP in g.columns else ""
                })

                # reinicia bloque
                current_city = city_i
                start_day = day_i
                end_day = day_i
                sum_hours = hours_i

        # cierra último bloque
        if current_city is not None:
            duration = (end_day - start_day + 1)
            blocks.append({
                "Responsable": tech,
                "Ciudad": current_city,
                "Inicio_dia": int(start_day),
                "Fin_dia": int(end_day),
                "Duracion_dias": int(duration),
                "Horas_instal_total": float(sum_hours),
                "GPS_inst_total": float(sum_hours / 0.75) if sum_hours > 0 else 0.0,
                "Duerme_en_fin": str(g.loc[len(g)-1, COL_SLEEP]) if COL_SLEEP in g.columns else ""
            })

    gantt_base = pd.DataFrame(blocks)
    if gantt_base.empty:
        print("[WARN] No se generaron bloques (quizás faltan días/ciudades). Exporto vacío.")
        gantt_base = pd.DataFrame(columns=[
            "Responsable", "Ciudad", "Inicio_dia", "Fin_dia", "Duracion_dias",
            "Horas_instal_total", "GPS_inst_total", "Duerme_en_fin"
        ])

    gantt_base = maybe_add_dates(gantt_base)


# =========================
# 4) EXPORT EXCEL BASE
# =========================
out_xlsx = os.path.join(OUTPUTS_DIR, "tabla_gantt_base.xlsx")
with pd.ExcelWriter(out_xlsx) as w:
    gantt_base.to_excel(w, index=False, sheet_name="Gantt_Base")
    df_plan.to_excel(w, index=False, sheet_name="Plan_Diario_Raw")

print(f"[OK] Tabla base exportada: {out_xlsx}")


# =========================
# 5) GANTT HTML (Plotly)
# =========================
# Gantt por técnico: barras por ciudad
if gantt_base.empty:
    print("[WARN] gantt_base vacío, no se generan HTML.")
else:
    # Para plotly, usamos Inicio_dia/Fin_dia numéricos (más robusto que texto)
    df_plot = gantt_base.copy()
    df_plot["Inicio_num"] = df_plot["Inicio_dia"]
    df_plot["Fin_num"] = df_plot["Fin_dia"]

    # 5.1 Gantt por técnico
    fig1 = px.timeline(
        df_plot,
        x_start="Inicio_num",
        x_end="Fin_num",
        y="Responsable",
        color="Ciudad",
        hover_data=["Duracion_dias", "Horas_instal_total", "GPS_inst_total", "Duerme_en_fin"],
        title="Carta Gantt – Operación Internos (por técnico)"
    )
    fig1.update_yaxes(autorange="reversed")
    fig1.update_layout(xaxis_title="Día del proyecto", yaxis_title="Técnico")

    out_html_1 = os.path.join(OUTPUTS_DIR, "gantt_operacion_internos.html")
    fig1.write_html(out_html_1)
    print(f"[OK] Gantt internos exportada: {out_html_1}")

    # 5.2 Gantt por ciudad (ordenado por inicio)
    df_city = df_plot.sort_values(["Inicio_dia", "Ciudad"]).copy()
    fig2 = px.timeline(
        df_city,
        x_start="Inicio_num",
        x_end="Fin_num",
        y="Ciudad",
        color="Responsable",
        hover_data=["Duracion_dias", "Horas_instal_total", "GPS_inst_total", "Duerme_en_fin"],
        title="Carta Gantt – Cliente / Ciudades (quién atiende cada ciudad)"
    )
    fig2.update_yaxes(autorange="reversed")
    fig2.update_layout(xaxis_title="Día del proyecto", yaxis_title="Ciudad")

    out_html_2 = os.path.join(OUTPUTS_DIR, "gantt_cliente_ciudades.html")
    fig2.write_html(out_html_2)
    print(f"[OK] Gantt ciudades exportada: {out_html_2}")

print("[DONE] Listo.")
