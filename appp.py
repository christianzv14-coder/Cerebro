import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ============================
# CONFIGURACIÓN GENERAL
# ============================
st.set_page_config(
    page_title="Predictivo MB por Patente",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Predictivo de Consumo MB por Patente (Límite 30 MB)")
st.markdown("---")

# ============================
# CARGA DEL ARCHIVO
# ============================
@st.cache_data
def load_data():
    df = pd.read_excel("Reporte_exceso_reg.xlsx")
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df

df = load_data()

# ============================
# FILTROS LATERALES
# ============================
st.sidebar.header("Filtros")

df_filtrado = df.copy()

# ---- 1) RANGO DE FECHA ----
if "Fecha" in df_filtrado.columns:
    min_date = df_filtrado["Fecha"].min()
    max_date = df_filtrado["Fecha"].max()

    if pd.notna(min_date) and pd.notna(max_date):
        fecha_ini, fecha_fin = st.sidebar.date_input(
            "Rango de Fecha",
            (min_date.date(), max_date.date())
        )

        mask_fecha = (
            (df_filtrado["Fecha"].dt.date >= fecha_ini) &
            (df_filtrado["Fecha"].dt.date <= fecha_fin)
        )
        df_filtrado = df_filtrado[mask_fecha]

# ---- 2) FILTRO DE CUENTA (PADRE DE PATENTE) ----
cuentas_disponibles = (
    df_filtrado["Cuenta"].dropna().unique().tolist()
    if "Cuenta" in df_filtrado.columns else []
)

cuentas_sel = []
if cuentas_disponibles:
    cuentas_sel = st.sidebar.multiselect("Cuenta", cuentas_disponibles)

    if cuentas_sel:
        df_filtrado = df_filtrado[df_filtrado["Cuenta"].isin(cuentas_sel)]

# ---- 3) OTROS FILTROS CATEGÓRICOS (EXCEPTO Fecha, Cuenta, Patente) ----
for col in df.columns:
    if col in ["Fecha", "Cuenta", "Patente"]:
        continue

    if df[col].dtype == "object":
        opciones = df_filtrado[col].dropna().unique().tolist()
        if not opciones:
            continue
        seleccion = st.sidebar.multiselect(col, opciones)
        if seleccion:
            df_filtrado = df_filtrado[df_filtrado[col].isin(seleccion)]

# ============================
# SELECTOR ÚNICO DE PATENTE (MANDA EN AMBOS GRÁFICOS)
# ============================
patente_sel = None
if "Patente" in df_filtrado.columns:
    patentes_disponibles = df_filtrado["Patente"].dropna().unique().tolist()

    if not patentes_disponibles:
        st.info("No hay patentes disponibles con los filtros actuales.")
    else:
        st.subheader("🚗 Patente")
        patente_sel = st.selectbox(
            "Selecciona una Patente para analizar:",
            patentes_disponibles
        )

st.markdown("---")

# ============================
# GRÁFICO 1: MB ACUM + RESTANTE POR PATENTE
# ============================
st.subheader("📊 MB Acum y MB Restante por Patente (límite 30 MB)")

UMBRAL_MB = 30  # límite por patente

if {"Patente", "MB"}.issubset(df_filtrado.columns) and patente_sel is not None:

    df_filtrado["MB"] = pd.to_numeric(df_filtrado["MB"], errors="coerce").fillna(0)

    # Agrupamos por patente dentro del filtro actual
    df_pat = df_filtrado.groupby("Patente", as_index=False)["MB"].sum()
    df_pat["MB Acum"] = df_pat["MB"]
    df_pat["MB Restante"] = (UMBRAL_MB - df_pat["MB Acum"]).clip(lower=0)

    # 👉 Filtrar SOLO a la patente seleccionada
    df_pat_sel = df_pat[df_pat["Patente"] == patente_sel]

    fig_stack = px.bar(
        df_pat_sel,
        x="Patente",
        y=["MB Acum", "MB Restante"],
        barmode="stack",
        title=f"MB Acumulado vs MB Restante para Patente {patente_sel} (capacidad {UMBRAL_MB} MB)",
    )

    fig_stack.update_layout(
        xaxis_title="Patente",
        yaxis_title="MB",
        xaxis_tickangle=0,
        legend_title_text=""
    )

    st.plotly_chart(fig_stack, use_container_width=True)
else:
    st.warning("No se encontraron las columnas necesarias 'Patente' y 'MB' o no hay patente seleccionada.")

st.markdown("---")

# ============================
# GRÁFICO 2: PREDICTIVO POR LA MISMA PATENTE
# ============================
st.subheader("🔮 Predictivo de Consumo por Patente")

if patente_sel is not None and {"Patente", "Fecha", "MB"}.issubset(df_filtrado.columns):

    df_p = df_filtrado[df_filtrado["Patente"] == patente_sel].copy()

    if df_p.empty:
        st.info("No hay datos para la patente seleccionada con los filtros actuales.")
    else:
        df_p["MB"] = pd.to_numeric(df_p["MB"], errors="coerce").fillna(0)
        df_p = df_p.dropna(subset=["Fecha"])
        df_p = df_p.sort_values("Fecha")

        # Acumulado real
        df_p["Acum_real"] = df_p["MB"].cumsum()

        # Promedio diario
        dias_distintos = df_p["Fecha"].dt.date.nunique()
        consumo_total = df_p["MB"].sum()

        if dias_distintos == 0:
            consumo_prom = 0
        else:
            consumo_prom = consumo_total / dias_distintos

        # Fechas para proyección
        hoy = df_p["Fecha"].max()

        if hoy.month == 12:
            fin_mes = datetime(hoy.year, 12, 31)
        else:
            fin_mes = datetime(hoy.year, hoy.month + 1, 1) - timedelta(days=1)

        dias_restantes = max(0, (fin_mes.date() - hoy.date()).days)

        proyeccion_total = consumo_total + consumo_prom * dias_restantes

        # Día estimado de sobreconsumo
        dia_exceso = None
        if consumo_prom > 0:
            mb_faltante = UMBRAL_MB - consumo_total
            if mb_faltante <= 0:
                dia_exceso = hoy  # ya está pasado
            else:
                dias_hasta_exceso = mb_faltante / consumo_prom
                dia_exceso = hoy + timedelta(days=dias_hasta_exceso)

        # ---------- Gráfico ----------
        fig_pred = go.Figure()

        # Real
        fig_pred.add_trace(go.Scatter(
            x=df_p["Fecha"],
            y=df_p["Acum_real"],
            mode="lines+markers",
            name="Acumulado Real"
        ))

        # Proyección
        if consumo_prom > 0 and dias_restantes > 0:
            fechas_proy = pd.date_range(hoy, fin_mes, freq="D")
            base = df_p["Acum_real"].iloc[-1]
            valores_proy = base + consumo_prom * (fechas_proy - hoy).days

            fig_pred.add_trace(go.Scatter(
                x=fechas_proy,
                y=valores_proy,
                mode="lines",
                name="Proyección",
                line=dict(dash="dash")
            ))

        # Línea límite
        fig_pred.add_hline(
            y=UMBRAL_MB,
            line=dict(color="red", dash="dot"),
            annotation_text=f"Límite {UMBRAL_MB} MB",
            annotation_position="top right"
        )

        fig_pred.update_layout(
            title=f"Predictivo de Consumo para Patente {patente_sel}",
            xaxis_title="Fecha",
            yaxis_title="MB Acumulado"
        )

        st.plotly_chart(fig_pred, use_container_width=True)

        # ---------- Resumen ejecutivo ----------
        st.markdown("### 📌 Resumen del Modelo Predictivo")

        st.write(f"**Consumo total actual:** {consumo_total:.2f} MB")
        st.write(f"**Consumo diario promedio:** {consumo_prom:.2f} MB/día")
        st.write(f"**MB proyectado al fin de mes:** {proyeccion_total:.2f} MB")

        if consumo_prom == 0:
            st.info("No hay suficiente variación de consumo para proyectar tendencia.")
        else:
            if proyeccion_total > UMBRAL_MB:
                st.error("⚠️ Se proyecta que la patente superará el límite de 30 MB este mes.")
                if dia_exceso is not None:
                    st.write(f"   • Día aproximado de sobreconsumo: **{dia_exceso.date()}**")
            else:
                st.success("✅ No se proyecta que la patente supere el límite de 30 MB este mes.")
else:
    if patente_sel is None:
        st.info("Selecciona una patente para ver el análisis predictivo.")
    else:
        st.warning("No se encontraron las columnas 'Patente', 'Fecha' y 'MB' necesarias para el predictivo.")
