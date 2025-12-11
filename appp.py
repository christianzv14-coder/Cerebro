import streamlit as st
import pandas as pd
import plotly.express as px

# ============================
# CONFIGURACIÓN GENERAL
# ============================
st.set_page_config(
    page_title="Reporte Exceso Reg - Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dashboard Exceso Reg")
st.markdown("Visualización interactiva basada en la sabana entregada.")

# ============================
# CARGA DEL ARCHIVO
# ============================
@st.cache_data
def load_data():
    ruta = "Reporte_exceso_reg.xlsx"  # Debe estar en la misma carpeta del app.py
    df = pd.read_excel(ruta)
    return df

df = load_data()

st.subheader("📁 Vista general del dataset")
st.dataframe(df, use_container_width=True)

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

st.subheader("📌 Data filtrada")
st.dataframe(df_filtrado, use_container_width=True)

# ============================
# GRÁFICO AUTOMÁTICO
# ============================
st.subheader("📈 Gráfico dinámico")

columnas_num = df_filtrado.select_dtypes(include=['int64', 'float64']).columns.tolist()
columnas_cat = df_filtrado.select_dtypes(include=['object']).columns.tolist()

if columnas_cat and columnas_num:
    eje_x = st.selectbox("Eje X (categoría)", columnas_cat)
    eje_y = st.selectbox("Eje Y (valor numérico)", columnas_num)

    fig = px.bar(df_filtrado, x=eje_x, y=eje_y, color=eje_x, title="Distribución por categoría")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay suficientes columnas categóricas o numéricas para graficar.")

# ============================
# DESCARGA DEL DATASET
# ============================
st.subheader("⬇️ Descargar datos filtrados")

def convertir_excel(df):
    from io import BytesIO
    buffer = BytesIO()
    df.to_excel(buffer, index=False, sheet_name="Filtrado")
    buffer.seek(0)
    return buffer

st.download_button(
    label="Descargar Excel filtrado",
    data=convertir_excel(df_filtrado),
    file_name="data_filtrada.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

