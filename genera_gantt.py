# genera_gantt.py
# ------------------------------------------------------------
# Carta Gantt desde archivo resultado_optimizacion_gps*.xlsx
# - No hardcodea el nombre del Excel
# - Busca automáticamente el último "resultado_optimizacion_gps*.xlsx"
# - Detecta la hoja con columnas: tecnico, dia, ciudad_trabajo
# - Exporta gantt_operativo.html en la misma carpeta del script
# ------------------------------------------------------------

import os
import glob
import pandas as pd
import plotly.express as px

# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATRON_RESULTADO = "resultado_optimizacion_gps*.xlsx"
OUTPUT_HTML = os.path.join(BASE_DIR, "gantt_operativo.html")


def buscar_archivo_resultado() -> str:
    """Busca el Excel más reciente que matchee el patrón en el directorio del script."""
    candidatos = glob.glob(os.path.join(BASE_DIR, PATRON_RESULTADO))
    if not candidatos:
        raise FileNotFoundError(
            f"No encontré ningún archivo '{PATRON_RESULTADO}' en:\n{BASE_DIR}\n"
            f"Solución rápida: copia tu Excel de resultado a esta carpeta o ejecuta el script desde la carpeta correcta."
        )
    return max(candidatos, key=os.path.getmtime)


def detectar_hoja_plan(xls: pd.ExcelFile) -> str:
    """Encuentra la hoja que contiene las columnas necesarias para construir el Gantt."""
    required = {"tecnico", "dia", "ciudad_trabajo"}
    for sh in xls.sheet_names:
        try:
            tmp = pd.read_excel(xls, sh, nrows=10)
            cols = {c.strip().lower() for c in tmp.columns}
            if required.issubset(cols):
                return sh
        except Exception:
            continue
    raise ValueError(
        "No encontré una hoja con columnas: tecnico, dia, ciudad_trabajo.\n"
        "Revisa nombres de columnas (deben ser exactamente esos, o al menos en minúscula con esos nombres)."
    )


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nombres de columnas a minúscula y sin espacios."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Renombres tolerantes si vinieran con tildes u otro texto
    rename_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if cl in ("técnico", "tecnico"):
            rename_map[c] = "tecnico"
        if cl in ("día", "dia"):
            rename_map[c] = "dia"
        if cl in ("ciudad trabajo", "ciudad_trabajo", "ciudad"):
            # OJO: aquí asumimos que si existe ciudad_trabajo ya está bien;
            # si no, tomamos "ciudad trabajo" / "ciudad" como fallback.
            if "ciudad_trabajo" not in df.columns:
                rename_map[c] = "ciudad_trabajo"

    if rename_map:
        df = df.rename(columns=rename_map)

    required = {"tecnico", "dia", "ciudad_trabajo"}
    if not required.issubset(set(df.columns)):
        faltan = required - set(df.columns)
        raise ValueError(f"Faltan columnas requeridas: {faltan}. Columnas disponibles: {list(df.columns)}")

    return df


def main():
    print("[INFO] RUNNING FILE:", os.path.abspath(__file__))

    archivo = buscar_archivo_resultado()
    print("[INFO] Archivo resultado usado:", archivo)

    xls = pd.ExcelFile(archivo)
    hoja = detectar_hoja_plan(xls)
    print("[INFO] Hoja plan usada:", hoja)

    df = pd.read_excel(xls, hoja)
    df = normalizar_columnas(df)

    # Asegurar tipos
    df["tecnico"] = df["tecnico"].astype(str).str.strip()
    df["ciudad_trabajo"] = df["ciudad_trabajo"].astype(str).str.strip()
    df["dia"] = pd.to_numeric(df["dia"], errors="coerce")

    df = df.dropna(subset=["dia"])
    df["dia"] = df["dia"].astype(int)

    # Orden
    df = df.sort_values(["tecnico", "dia"]).reset_index(drop=True)

    # Timeline: día a día (barra de 1 día)
    df["inicio"] = df["dia"]
    df["fin"] = df["dia"] + 1

    fig = px.timeline(
        df,
        x_start="inicio",
        x_end="fin",
        y="tecnico",
        color="ciudad_trabajo",
        title="Carta Gantt – Plan Operativo GPS",
        hover_data=["dia", "ciudad_trabajo"]
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        xaxis_title="Día del proyecto",
        yaxis_title="Técnico",
        legend_title="Ciudad"
    )

    fig.write_html(OUTPUT_HTML)
    print("[OK] Gantt generado:", OUTPUT_HTML)


if __name__ == "__main__":
    main()
