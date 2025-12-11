import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# ============================
# CONFIGURACIÓN GENERAL
# ============================
st.set_page_config(
    page_title="REPORTE EXCESO REG - MB por Patente",
    page_icon="📊",
    layout="wide"
)

st.title("📊 REPORTE EXCESO REG - MB por Patente")
st.markdown("Dash para ver **MB usada vs capacidad 30.720 MB por Patente**.")
st.markdown("---")

# ============================
# CARGA DEL ARCHIVO
# ============================
@st.cache_data
def load_data():
    ruta = "Reporte_exceso_reg.xlsx"  # Debe estar en la misma carpeta del appp.py
    df = pd.read_excel(ruta)
    return df

df = load_data()

# ============================
# FILTROS LATERALES
# ============================
st.sidebar.header("Filtros")

filtros = {}

for col in df.columns:
    if df[col].dtype == "object":
        opciones = df[col].dropna().unique().tolist()
        seleccion = st.sidebar.multiselect(col, opciones)
        if seleccion:
            filtros[col] = seleccion

# Aplicar filtros
df_filtrado = df.copy()
for col, valores in filtros.items():
    df_filtrado = df_filtrado[df_filtrado[col].isin(valores)]

st.subheader("📁 Data filtrada")
st.dataframe(df_filtrado, use_container_width=True)

st.markdown("---")

# ============================
# GRÁFICO: MB ACUM y MB RESTANTE POR PATENTE (USANDO COLUMNA MB)
# ============================
st.subheader("📊 MB Acum y MB Restante por Patente (desde columna MB)")

UMBRAL_MB = 30  # capacidad objetivo

# Validar que existan las columnas necesarias
if "Patente" in df_filtrado.columns and "MB" in df_filtrado.columns:
    # 1) Agrupar por Patente y sumar MB
    df_pat = (
        df_filtrado
        .groupby("Patente", as_index=False)["MB"]
        .sum()
    )

    # 2) Renombrar MB como MB Acum y calcular MB Restante
    df_pat["MB Acum"] = df_pat["MB"]
    df_pat["MB Restante"] = (UMBRAL_MB - df_pat["MB Acum"]).clip(lower=0)

    # 3) Ordenar por MB Acum (de mayor a menor)
    df_pat = df_pat.sort_values("MB Acum", ascending=False)

    # 4) Pasar a formato largo para gráfico apilado
    df_long = df_pat.melt(
        id_vars="Patente",
        value_vars=["MB Acum", "MB Restante"],
        var_name="Tipo",
        value_name="MB"
    )

    # 5) Gráfico de barras apiladas
    fig_stack = px.bar(
        df_long,
        x="Patente",
        y="MB",
        color="Tipo",
        barmode="stack",
        title=f"MB Acum y MB Restante por Patente (capacidad {UMBRAL_MB} MB)",
    )

    fig_stack.update_layout(
        xaxis_title="Patente",
        yaxis_title="MB Acum y MB Restante",
        xaxis_tickangle=45
    )

    st.plotly_chart(fig_stack, use_container_width=True)

    st.subheader("📋 Tabla resumen por Patente")
    st.dataframe(df_pat[["Patente", "MB Acum", "MB Restante"]], use_container_width=True)

else:
    st.warning("No se encontraron las columnas 'Patente' y 'MB' en el dataset.")

st.markdown("---")

# ============================
# DESCARGA DEL DATASET FILTRADO
# ============================
st.subheader("⬇️ Descargar datos filtrados")

def convertir_excel(df_in):
    buffer = BytesIO()
    df_in.to_excel(buffer, index=False, sheet_name="Filtrado")
    buffer.seek(0)
    return buffer

st.download_button(
    label="Descargar Excel filtrado",
    data=convertir_excel(df_filtrado),
    file_name="data_filtrada.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
