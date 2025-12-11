import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime

# ============================
# CONFIGURACIÓN
# ============================
st.set_page_config(page_title="Predictivo MB por Patente", page_icon="📊", layout="wide")
st.title("📊 Predictivo de Consumo MB por Patente (Límite 30 MB)")
st.markdown("---")

# ============================
# CARGAR DATA
# ============================
@st.cache_data
def load_data():
    df = pd.read_excel("Reporte_exceso_reg.xlsx")
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df

df = load_data()

# ============================
# FILTRO: RANGO DE FECHAS
# ============================
st.sidebar.header("Filtros")

df_filtrado = df.copy()

if "Fecha" in df_filtrado.columns:
    min_date = df_filtrado["Fecha"].min()
    max_date = df_filtrado["Fecha"].max()

    fecha_ini, fecha_fin = st.sidebar.date_input(
        "Rango de Fecha",
        (min_date.date(), max_date.date())
    )

    mask = (df_filtrado["Fecha"].dt.date >= fecha_ini) & (df_filtrado["Fecha"].dt.date <= fecha_fin)
    df_filtrado = df_filtrado[mask]

# ============================
# FILTROS CATEGÓRICOS
# ============================
for col in df.columns:
    if col in ["Fecha"]:
        continue

    if df[col].dtype == object:
        opciones = df[col].dropna().unique().tolist()
        seleccion = st.sidebar.multiselect(col, opciones)
        if seleccion:
            df_filtrado = df_filtrado[df_filtrado[col].isin(seleccion)]

# ============================
# GRÁFICO 1: MB ACUM + RESTANTE
# ============================
if "Patente" in df_filtrado.columns and "MB" in df_filtrado.columns:

    df_filtrado["MB"] = pd.to_numeric(df_filtrado["MB"], errors="coerce").fillna(0)

    df_pat = df_filtrado.groupby("Patente", as_index=False)["MB"].sum()
    df_pat["MB Acum"] = df_pat["MB"]
    df_pat["MB Restante"] = (30 - df_pat["MB Acum"]).clip(lower=0)
    df_pat = df_pat.sort_values("MB Acum", ascending=False)

    fig = px.bar(
        df_pat,
        x="Patente",
        y=["MB Acum", "MB Restante"],
        title="MB Acumulado vs MB Restante (Límite 30 MB)",
        barmode="stack"
    )
    fig.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

# ============================
# GRÁFICO 2: PREDICTIVO
# ============================
st.subheader("🔮 Predictivo de Consumo por Patente")

if "Patente" in df_filtrado.columns:

    patentes = df_filtrado["Patente"].unique()
    patente_sel = st.selectbox("Selecciona una Patente para analizar:", patentes)

    df_p = df_filtrado[df_filtrado["Patente"] == patente_sel].copy()

    # Ordenar por fecha
    df_p = df_p.sort_values("Fecha")

    # Acumulado real
    df_p["Acum_real"] = df_p["MB"].cumsum()

    # Promedio diario
    dias_distintos = df_p["Fecha"].dt.date.nunique()
    consumo_prom = df_p["MB"].sum() / dias_distintos

    # Proyección lineal hasta fin de mes
    hoy = df_p["Fecha"].max()
    fin_mes = datetime(hoy.year, hoy.month + 1, 1) - pd.Timedelta(days=1)
    dias_restantes = (fin_mes.date() - hoy.date()).days

    proyeccion_total = df_p["MB"].sum() + consumo_prom * dias_restantes

    # Día estimado de sobreconsumo
    if consumo_prom > 0:
        dias_hasta_exceso = max(0, (30 - df_p["MB"].sum()) / consumo_prom)
        dia_exceso = hoy + pd.Timedelta(days=dias_hasta_exceso)
    else:
        dia_exceso = None

    # Graficar tendencia real + proyección
    fig2 = go.Figure()

    # Real
    fig2.add_trace(go.Scatter(
        x=df_p["Fecha"],
        y=df_p["Acum_real"],
        mode="lines+markers",
        name="Acumulado Real"
    ))

    # Proyección (solo si tiene promedio > 0)
    if consumo_prom > 0:
        fechas_proy = pd.date_range(hoy, fin_mes, freq="D")
        valores_proy = df_p["Acum_real"].iloc[-1] + consumo_prom * (fechas_proy - hoy).days

        fig2.add_trace(go.Scatter(
            x=fechas_proy,
            y=valores_proy,
            mode="lines",
            name="Proyección",
            line=dict(dash="dash")
        ))

    # Línea límite
    fig2.add_hline(y=30, line=dict(color="red", dash="dot"), annotation_text="Límite 30 MB")

    fig2.update_layout(title=f"Predictivo de Consumo para Patente {patente_sel}",
                       xaxis_title="Fecha",
                       yaxis_title="MB Acumulado")

    st.plotly_chart(fig2, use_container_width=True)

    # ============================
    # RESULTADOS CLAVE
    # ============================
    st.markdown("### 📌 Resultados del Modelo Predictivo")

    st.write(f"**Consumo diario promedio:** {consumo_prom:.2f} MB/día")
    st.write(f"**MB actual:** {df_p['MB'].sum():.2f} MB")
    st.write(f"**MB proyectado al fin de mes:** {proyeccion_total:.2f} MB")

    if dia_exceso:
        if proyeccion_total > 30:
            st.error(f"⚠️ Se proyecta que la patente **superará los 30 MB** alrededor del **{dia_exceso.date()}**.")
        else:
            st.success("No se proyecta que supere los 30 MB este mes.")
    else:
        st.info("No hay suficiente información para proyectar sobreconsumo.")
