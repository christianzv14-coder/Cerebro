import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# ============================
# CONFIGURACIÓN GENERAL
# ============================
st.set_page_config(
    page_title="REPORTE EXCESO REG - ACUMULADO V2",
    page_icon="📊",
    layout="wide"
)

st.title("📊 REPORTE EXCESO REG - ACUMULADO V2")
st.markdown("Esta versión SOLO tiene el gráfico **acumulado por Cuenta**.")
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
# GRÁFICO ACUMULADO POR CUENTA (Tam Log)
# ============================
st.subheader("📈 Acumulado de Tam Log por Cuenta hasta 30.720")

UMBRAL = 30720

if "Cuenta" in df_filtrado.columns and "Tam Log" in df_filtrado.columns:
    # 1) Agrupar por cuenta y sumar Tam Log (respetando filtros)
    df_cuentas = (
        df_filtrado
        .groupby("Cuenta", as_index=False)["Tam Log"]
        .sum()
    )

    # 2) Ordenar de mayor a menor Tam Log
    df_cuentas = df_cuentas.sort_values("Tam Log", ascending=False)

    # 3) Calcular acumulado
    df_cuentas["Acumulado"] = df_cuentas["Tam Log"].cumsum()

    # 4) Quedarnos con las cuentas necesarias hasta llegar al umbral
    df_sel = df_cuentas[df_cuentas["Acumulado"] <= UMBRAL]

    # Si el último acumulado es menor al umbral, sumamos la primera cuenta que lo sobrepasa
    if not df_cuentas[df_cuentas["Acumulado"] > UMBRAL].empty:
        primera_sobre = df_cuentas[df_cuentas["Acumulado"] > UMBRAL].head(1)
        df_sel = pd.concat([df_sel, primera_sobre]).drop_duplicates(subset=["Cuenta"])

    if df_sel.empty:
        st.info("Con los filtros actuales no se alcanza el acumulado de 30.720 Tam Log.")
    else:
        fig_acum = px.line(
            df_sel,
            x="Cuenta",
            y="Acumulado",
            markers=True,
            title="Acumulado de Tam Log por Cuenta (corte en 30.720)",
        )

        fig_acum.add_hline(
            y=UMBRAL,
            line_dash="dash",
            annotation_text="Objetivo 30.720",
            annotation_position="top left"
        )

        fig_acum.update_layout(xaxis_tickangle=45)

        st.plotly_chart(fig_acum, use_container_width=True)

        st.subheader("📋 Tabla usada en el acumulado")
        st.dataframe(df_sel, use_container_width=True)
else:
    st.warning("No se encontraron las columnas 'Cuenta' y 'Tam Log' en el dataset.")

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
