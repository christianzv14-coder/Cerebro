
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Cerebro Patio | Inventory Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_RAW = os.path.join(BASE_DIR, 'data', 'input_actividades.xlsx')
DATA_OPT = os.path.join(BASE_DIR, 'outputs', 'Inventario_Escenario_3_OPTIMIZADO_FINAL.xlsx')

import shutil
import uuid

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # Helper to clean read locked files
    def safe_read(filepath, sheet):
        if not os.path.exists(filepath):
            return pd.DataFrame()
        
        # Unique temp file to avoid collisions
        temp_path = os.path.join(os.path.dirname(filepath), f"temp_dash_{uuid.uuid4().hex[:8]}.xlsx")
        try:
            shutil.copy2(filepath, temp_path)
            return pd.read_excel(temp_path, sheet_name=sheet, engine='openpyxl')
        except Exception as e:
            st.warning(f"⚠️ Error leyendo {sheet}: {e}")
            return pd.DataFrame()
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass

    # 1. Load Optimization Results (KPIs + Projects)
    if not os.path.exists(DATA_OPT):
        st.error("⚠️ No se encuentra el archivo de inventario optimizado. Ejecuta 'run_scenarios_v3' primero.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_kpi = safe_read(DATA_OPT, 'Reporte_Compras')
    df_projects = safe_read(DATA_OPT, 'Proyectos_Detectados')

    # 2. Load Raw History
    # Also safe read if possible, usually raw is not locked but good practice
    df_raw = pd.DataFrame()
    if os.path.exists(DATA_RAW):
        # We handle raw simpler since it's just one sheet usually
        temp_raw = os.path.join(os.path.dirname(DATA_RAW), f"temp_raw_{uuid.uuid4().hex[:8]}.xlsx")
        try:
            shutil.copy2(DATA_RAW, temp_raw)
            df_raw = pd.read_excel(temp_raw)
            if 'fecha' in df_raw.columns:
                df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
        except:
            pass
        finally:
            try:
                if os.path.exists(temp_raw):
                    os.remove(temp_raw)
            except:
                pass
        
    return df_kpi, df_projects, df_raw

df_kpi, df_projects, df_raw = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.title("🎛️ Filtros Ejecutivos")
st.sidebar.markdown("---")

# 1. Filter SKU
all_skus = sorted(df_kpi['SKU'].unique())
selected_skus = st.sidebar.multiselect("📦 Filtrar SKU (Accesorio)", all_skus, default=all_skus[:5]) # Select top 5 by default

# 2. Filter Client (Applies to Raw Data mainly)
if 'cliente' in df_raw.columns: # Assuming raw has 'cliente' or similar from previous steps
    all_clients = sorted(df_raw['cliente'].astype(str).unique())
    selected_clients = st.sidebar.multiselect("🏢 Filtrar Cliente", all_clients)
else:
    selected_clients = []

# Filter Dataframes
filtered_kpi = df_kpi[df_kpi['SKU'].isin(selected_skus)]

# --- MAIN DASHBOARD ---
st.title("🧠 Cerebro Patio: Dashboard de Inventario")
st.markdown("### Optimización Híbrida (Forecast + Política de Riesgo)")
st.markdown("---")

# --- TOP KPI METRICS ---
c1, c2, c3, c4 = st.columns(4)
total_skus = len(filtered_kpi)
total_order_qty = filtered_kpi['Cantidad_A_Pedir'].sum()
total_ss = filtered_kpi['Stock_Seguridad'].sum()
avg_service = "95%" # Fixed Policy

c1.metric("📦 SKUs Analizados", total_skus)
c2.metric("🛒 A Pedir (Unidades)", f"{int(total_order_qty):,}")
c3.metric("🛡️ Stock Seguridad Total", f"{int(total_ss):,}")
c4.metric("🎯 Nivel Servicio Objetivo", avg_service)

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Estrategia ABC", "📈 Demanda & Forecast", "🚨 Alertas Stock", "🧹 Proyectos Limpiados"])

# === TAB 1: ABC ===
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Distribución ABC")
        if not filtered_kpi.empty:
            fig_sun = px.sunburst(
                filtered_kpi, 
                path=['Clasificación', 'SKU'], 
                values='Forecast_Prom_Q',
                color='Clasificación',
                color_discrete_map={'A': '#EF553B', 'B': '#636EFA', 'C': '#00CC96'},
                title="Peso del Portafolio (por Volumen)"
            )
            st.plotly_chart(fig_sun, use_container_width=True)
            
    with col2:
        st.subheader("Análisis de Rotación")
        # Scatter: Forecast (Rotacion) vs Safety Stock (Investment)
        fig_scat = px.scatter(
            filtered_kpi,
            x="Forecast_Prom_Q",
            y="Stock_Seguridad",
            size="Punto_Reorden",
            color="Clasificación",
            hover_name="SKU",
            title="Mapa de Riesgo: Demanda vs Stock Seguridad",
            labels={"Forecast_Prom_Q": "Velocidad de Venta (Unid/Sem)", "Stock_Seguridad": "Inversión en Riesgo"}
        )
        st.plotly_chart(fig_scat, use_container_width=True)

# === TAB 2: TIME SERIES ===
with tab2:
    st.subheader("Evolución Temporal: Historia vs Proyección")
    
    if selected_skus:
        # Prepare Raw History Aggregated
        # Filter raw by SKU and Client
        raw_mask = df_raw['materiales_usados'].astype(str).str.contains('|'.join(selected_skus), case=False, na=False) 
        # Note: Raw filter is tricky string match, keeping it simple for visualization
        # Ideally we parse, but for viz approximation:
        
        # Let's iterate selected SKUs to build the graph
        for sku in selected_skus:
            # 1. History
            # This is a rough approximation reading the raw string again. 
            # Ideally use expanded data, but we don't store it. 
            # We will show the KPI Scalar Forecast as a line.
            
            # Forecast Line
            kpi_row = df_kpi[df_kpi['SKU'] == sku]
            if not kpi_row.empty:
                forecast_val = kpi_row['Forecast_Prom_Q'].values[0]
                ss_val = kpi_row['Stock_Seguridad'].values[0]
                
                # Mock Time Series for Visualization (Since we don't have perfect weekly history in memory)
                # Visual Trick: Show the constant levels
                st.markdown(f"#### {sku}")
                
                # Gauge Chart for Coverage
                g1, g2, g3 = st.columns(3)
                g1.metric("Pronóstico Semanal", f"{forecast_val} u")
                g2.metric("Stock Seguridad", f"{ss_val} u")
                g3.metric("Punto Reorden", f"{kpi_row['Punto_Reorden'].values[0]} u")
                
                st.divider()

    else:
        st.info("Selecciona SKUs en la barra lateral para ver detalles.")

# === TAB 3: ALERTAS ===
with tab3:
    st.subheader("🚨 Órdenes de Compra Sugeridas")
    st.markdown("SKUs donde `Punto Reorden >= Stock Actual`")

    if 'Stock_Actual' not in filtered_kpi.columns:
        filtered_kpi['Stock_Actual'] = 0
    
    urgent_df = filtered_kpi[filtered_kpi['Cantidad_A_Pedir'] > 0][['SKU', 'Clasificación', 'Cantidad_A_Pedir', 'Punto_Reorden', 'Stock_Actual']]
    urgent_df = urgent_df.sort_values('Cantidad_A_Pedir', ascending=False)
    
    st.dataframe(
        urgent_df,
        column_config={
            "Stock_Actual": st.column_config.NumberColumn("Stock Actual", format="%d"),
            "Cantidad_A_Pedir": st.column_config.ProgressColumn(
                "Cantidad a Pedir",
                help="Volumen urgente",
                format="%d",
                min_value=0,
                max_value=int(urgent_df['Cantidad_A_Pedir'].max()) if not urgent_df.empty else 100,
            ),
            "Punto_Reorden": st.column_config.NumberColumn("Punto Reorden", format="%d")
        },
        use_container_width=True
    )

# === TAB 4: REMOVED PROJECTS ===
with tab4:
    st.subheader("🧹 Proyectos Detectados y Eliminados")
    st.markdown("Estos eventos fueron identificados como **'Spikes de Proyecto'** y se restaron del cálculo de forecast para no ensuciar el promedio.")
    
    if not df_projects.empty:
        # Filter by selected SKU if any
        if selected_skus:
            proj_viz = df_projects[df_projects['SKU'].isin(selected_skus)]
        else:
            proj_viz = df_projects
            
        st.dataframe(proj_viz, use_container_width=True)
        
        # Chart
        st.subheader("Impacto por Cliente")
        count_by_cli = proj_viz.groupby('Cliente')['Qty'].sum().reset_index().sort_values('Qty', ascending=False)
        fig_bar = px.bar(count_by_cli, x='Cliente', y='Qty', title="Volumen Total Eliminado por Cliente")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.success("No se detectaron proyectos eliminados en este set de datos.")
