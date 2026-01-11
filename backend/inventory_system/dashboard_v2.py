
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import shutil
import uuid
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Cerebro Patio | Command Center",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_RAW = os.path.join(BASE_DIR, 'data', 'input_actividades.xlsx')
DATA_OPT = os.path.join(BASE_DIR, 'outputs', 'Inventario_Escenario_3_OPTIMIZADO_FINAL.xlsx')

# --- HELPER FUNCTIONS ---
def safe_read_excel(filepath, sheet_name=0):
    """Reads Excel file safely by copying to temp if locked."""
    if not os.path.exists(filepath):
        return pd.DataFrame()
    
    temp_path = os.path.join(os.path.dirname(filepath), f"temp_dash_{uuid.uuid4().hex[:8]}.xlsx")
    try:
        shutil.copy2(filepath, temp_path)
        return pd.read_excel(temp_path, sheet_name=sheet_name, engine='openpyxl')
    except Exception as e:
        # Fallback: try reading directly if copy failed (rare)
        try:
             return pd.read_excel(filepath, sheet_name=sheet_name, engine='openpyxl')
        except:
             st.error(f"Error leyendo {filepath}: {e}")
             return pd.DataFrame()
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

@st.cache_data
def load_and_prep_data():
    # 1. Load Master Data (Optimization Output)
    df_master = safe_read_excel(DATA_OPT, sheet_name='Reporte_Compras')
    
    # 2. Load Projects (Exceptions)
    df_projects = safe_read_excel(DATA_OPT, sheet_name='Proyectos_Detectados')
    
    # 3. Load Raw Demand (History)
    df_raw = safe_read_excel(DATA_RAW)
    if 'fecha' in df_raw.columns:
        df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
    
    # --- PRE-CALCULATIONS & RULES ---
    if not df_master.empty:
        # Fill Missing Stock with 0 if not present
        if 'Stock_Actual' not in df_master.columns:
            df_master['Stock_Actual'] = 0
            
        # WOS (Weeks of Supply)
        # Avoid division by zero
        df_master['WOS'] = df_master.apply(
            lambda x: x['Stock_Actual'] / x['Forecast_Prom_Q'] if x['Forecast_Prom_Q'] > 0 else 999, axis=1
        )
        
        # Brecha ROP (Deficit)
        # Negative means under ROP (Risk)
        df_master['Brecha_ROP'] = df_master['Stock_Actual'] - df_master['Punto_Reorden']
        
        # Status
        def get_status(row):
            if row['Stock_Actual'] < row['Punto_Reorden']:
                return "🔴 Bajo ROP"
            elif row['Stock_Actual'] < row['Punto_Reorden'] + row['Stock_Seguridad']:
                return "🟡 Alerta"
            else:
                return "🟢 OK"
        
        df_master['Estado_Stock'] = df_master.apply(get_status, axis=1)
        
        # Forecast Health (Inferida por Sigma/Forecast)
        # Assuming Sigma is RMSE or similar deviation. 
        # CV = Sigma / Forecast. 
        # CV < 0.3 Good, 0.3-0.6 Fair, >0.6 Poor
        df_master['CV'] = df_master.apply(
            lambda x: x['Sigma_Riesgo'] / x['Forecast_Prom_Q'] if x['Forecast_Prom_Q'] > 0 else 0, axis=1
        )
        
        def get_health(cv):
            if cv < 0.3: return "🟢 Confiable"
            if cv < 0.6: return "🟡 Revisar"
            return "🔴 Volátil"
            
        df_master['Salud_Modelo'] = df_master['CV'].apply(get_health)
        
        # Priority Score for Replenishment
        # Higher score = More urgent
        # Factors: Is under ROP (binary), ABC (A=3, B=2, C=1), WOS (inverse)
        abc_weight = {'A': 3, 'B': 2, 'C': 1}
        df_master['Prioridad_Score'] = df_master.apply(
            lambda x: (10 if x['Brecha_ROP'] < 0 else 0) + 
                      (abc_weight.get(x['Clasificación'], 1) * 2) +
                      (10 / (x['WOS'] + 0.1)), axis=1
        )
        
    return df_master, df_projects, df_raw

df_master, df_projects, df_raw = load_and_prep_data()

# --- SIDEBAR FILTERS ---
st.sidebar.title("🎛️ Centro de Comando")

# Global Filters
st.sidebar.subheader("Filtros Globales")
mode = st.sidebar.radio("Modo de Vista", ["🏛️ Comité Ejecutivo", "⚙️ Operación Diaria"])

# 1. SKU Search (Primary)
if not df_master.empty:
    all_skus = sorted(df_master['SKU'].unique())
    search_sku = st.sidebar.selectbox("🔎 Buscar Accesorio", ["Todos"] + all_skus)
else:
    search_sku = "Todos"

# 2. ABC (Secondary)
selected_abc = st.sidebar.multiselect("Clasificación ABC", ['A', 'B', 'C'], default=['A', 'B', 'C'])

# Apply Logic
if not df_master.empty:
    if search_sku != "Todos":
        # Direct Match (Overrides ABC)
        df_filtered = df_master[df_master['SKU'] == search_sku]
    else:
        # Filter by ABC
        df_filtered = df_master[df_master['Clasificación'].isin(selected_abc)]
else:
    df_filtered = pd.DataFrame()

st.sidebar.markdown("---")
st.sidebar.info(f"SKUs Activos: {len(df_filtered)}")

# --- MAIN LAYOUT ---
st.title("🧠 Cerebro Patio: Inventory Intelligence")

if df_master.empty:
    st.warning("⚠️ No hay datos cargados. Por favor ejecuta la simulación primero.")
    st.stop()

# TABS
tab_cockpit, tab_repo, tab_risk, tab_forecast, tab_clients, tab_projects, tab_quality = st.tabs([
    "🚀 Cockpit", "🛒 Reposición", "🛡️ Riesgo", "🔮 Forecast", "🏢 Clientes", "🧹 Excepciones", "✅ Calidad"
])

# === 1. COCKPIT EJECUTIVO ===
with tab_cockpit:
    st.markdown("### 📊 Estado General del Inventario")
    
    # KPIs Row
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    # 1. % Bajo ROP
    n_under_rop = len(df_filtered[df_filtered['Brecha_ROP'] < 0])
    pct_under_rop = (n_under_rop / len(df_filtered)) * 100 if len(df_filtered) > 0 else 0
    kpi1.metric("🚨 Bajo ROP", f"{pct_under_rop:.1f}%", f"{n_under_rop} SKUs")
    
    # 2. Unidades en Riesgo (Total Deficit)
    market_deficit = df_filtered[df_filtered['Brecha_ROP'] < 0]['Brecha_ROP'].sum() * -1
    kpi2.metric("📉 Déficit Unidades", f"{int(market_deficit):,}")
    
    # 3. Volumen Sugerido Compra
    vol_buy = df_filtered['Cantidad_A_Pedir'].sum()
    kpi3.metric("🛒 A Reponer (Q)", f"{int(vol_buy):,}")
    
    # 4. Cobertura Mediana
    med_wos = df_filtered[df_filtered['WOS'] < 999]['WOS'].median()
    kpi4.metric("📅 Cobertura Típica", f"{med_wos:.1f} Semanas")
    
    # 5. Salud Modelo
    pct_reliable = (len(df_filtered[df_filtered['Salud_Modelo'] == "🟢 Confiable"]) / len(df_filtered)) * 100
    kpi5.metric("✅ Forecast Confiable", f"{pct_reliable:.0f}%")
    
    st.markdown("---")
    
    # Charts Row
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Estado de Stock por ABC")
        # Stacked Bar: ABC vs Estado_Stock
        status_counts = df_filtered.groupby(['Clasificación', 'Estado_Stock']).size().reset_index(name='SKUs')
        fig_status = px.bar(status_counts, x="Clasificación", y="SKUs", color="Estado_Stock", 
                            color_discrete_map={"🔴 Bajo ROP": "#EF553B", "🟡 Alerta": "#FFA15A", "🟢 OK": "#00CC96"},
                            title="Salud de Stock por Importancia (ABC)")
        st.plotly_chart(fig_status, use_container_width=True)
        
    with c2:
        st.subheader("Distribución de Cobertura (WOS)")
        # Histogram of WOS (filter outliers > 20 weeks)
        wos_data = df_filtered[df_filtered['WOS'] < 20]
        fig_wos = px.histogram(wos_data, x="WOS", color="Clasificación", nbins=20,
                               title="Semanas de Inventario (Histograma)",
                               color_discrete_map={'A': '#EF553B', 'B': '#636EFA', 'C': '#00CC96'})
        st.plotly_chart(fig_wos, use_container_width=True)
        
    # Top Risks Table
    st.subheader("🔥 Top 10 Riesgos Críticos")
    top_risks = df_filtered.sort_values('Prioridad_Score', ascending=False).head(10 if mode == "🏛️ Comité Ejecutivo" else 20)
    
    st.dataframe(
        top_risks[['SKU', 'Clasificación', 'Stock_Actual', 'Punto_Reorden', 'WOS', 'Cantidad_A_Pedir', 'Estado_Stock']],
        use_container_width=True,
        column_config={
            "WOS": st.column_config.NumberColumn("Semanas Cobertura", format="%.1f"),
            "Cantidad_A_Pedir": st.column_config.ProgressColumn("Sugerido Reponer", format="%d", min_value=0, max_value=int(top_risks['Cantidad_A_Pedir'].max()))
        }
    )

# === 2. REPOSICIÓN (ACTION CENTER) ===
with tab_repo:
    st.markdown("### 🛒 Centro de Reposición")
    
    col_params, col_viz = st.columns([1, 3])
    
    with col_params:
        st.caption("⚙️ Parámetros de Priorización")
        w_abc = st.slider("Peso ABC", 1, 5, 3)
        w_risk = st.slider("Peso Riesgo (Bajo ROP)", 1, 10, 10)
        
        filter_crit = st.checkbox("Ver solo CRÍTICOS (A + Rojo)", value=True)
        
    with col_viz:
        # Generate Action Table
        action_df = df_filtered.sort_values('Prioridad_Score', ascending=False).copy()
        
        if filter_crit:
            action_df = action_df[(action_df['Clasificación'] == 'A') & (action_df['Estado_Stock'] == "🔴 Bajo ROP")]
            
        st.info(f"Se sugieren **{len(action_df)} líneas de compra** críticas.")
        
        st.dataframe(
            action_df[['SKU', 'Clasificación', 'Stock_Actual', 'Punto_Reorden', 'Stock_Seguridad', 'Cantidad_A_Pedir']],
            use_container_width=True,
            column_config={
                 "Cantidad_A_Pedir": st.column_config.NumberColumn("Ordenar (Unidades)", format="%d", help="Cantidad para volver a nivel seguro")
            }
        )
        
        # Download Button
        csv = action_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Descargar Orden de Compra (CSV)",
            data=csv,
            file_name='orden_compra_sugerida.csv',
            mime='text/csv',
        )

# === 3. RIESGO ===
with tab_risk:
    st.markdown("### 🛡️ Mapa de Riesgo & Volatilidad")
    
    # Scatter: Risk (Sigma) vs Coverage (WOS)
    fig_risk = px.scatter(
        df_filtered[df_filtered['WOS'] < 52], # Trim outliers
        x="Sigma_Riesgo",
        y="WOS",
        color="Clasificación",
        size="Forecast_Prom_Q",
        hover_name="SKU",
        title="Mapa de Vulnerabilidad: Volatilidad vs Cobertura",
        labels={"Sigma_Riesgo": "Volatilidad (Incertidumbre)", "WOS": "Semanas de Cobertura"},
        color_discrete_map={'A': '#EF553B', 'B': '#636EFA', 'C': '#00CC96'}
    )
    # Add lines for "Danger Zone"
    fig_risk.add_hline(y=2, line_dash="dash", line_color="red", annotation_text="Zona Peligro (<2 sem)")
    st.plotly_chart(fig_risk, use_container_width=True)

# === 4. FORECAST ===
with tab_forecast:
    st.markdown("### 🔮 Auditoría de Forecast")
    
    c_list, c_detail = st.columns([1, 2])
    
    with c_list:
        st.caption("Top SKUs por Volatilidad (Más difíciles de predecir)")
        st.dataframe(
            df_filtered.sort_values('CV', ascending=False)[['SKU', 'Salud_Modelo', 'CV']].head(10),
            use_container_width=True
        )
        
    with c_detail:
        if search_sku != "Todos":
            target_sku = search_sku
        else:
            target_sku = df_filtered['SKU'].iloc[0] if not df_filtered.empty else None
            
        if target_sku:
            st.subheader(f"Análisis: {target_sku}")
            
            # Forecast vs History Logic
            # Try to filter raw data
            sku_row = df_filtered[df_filtered['SKU'] == target_sku].iloc[0]
            
            # KPI Card
            fk1, fk2, fk3 = st.columns(3)
            fk1.metric("Pronóstico Semanal", f"{sku_row['Forecast_Prom_Q']}")
            fk2.metric("Incertidumbre (Sigma)", f"{sku_row['Sigma_Riesgo']}")
            fk3.metric("Salud", sku_row['Salud_Modelo'])
            
            # Chart
            # We mock the time series visualization using the raw data if available
            raw_sku = df_raw[df_raw['materiales_usados'].astype(str).str.contains(target_sku, case=False, na=False)] if not df_raw.empty else pd.DataFrame()
            
            if not raw_sku.empty:
                # Aggregate by week
                raw_sku['Semana'] = raw_sku['fecha'].dt.to_period('W').apply(lambda r: r.start_time)
                # Need to extract quantity... this is parsing hell again. 
                # For this Dashboard V2, we will simplify: show aggregation of rows as proxy for frequency
                # Or better: Just show the static scalar Forecast vs History "presence".
                
                # Let's show the Projects Detected for this SKU
                st.write(" **Proyectos Eliminados (Spikes):**")
                if not df_projects.empty:
                    projs = df_projects[df_projects['SKU'] == target_sku]
                    if not projs.empty:
                        st.dataframe(projs)
                    else:
                        st.info("Sin proyectos detectados.")
            else:
                st.info("No hay historia raw disponible para graficar.")

# === 5. CLIENTES ===
with tab_clients:
    st.markdown("### 🏢 Concentración de Demanda")
    # Need Raw Data for this.
    if not df_raw.empty:
        # Count rows as proxy for demand frequency by client
        if 'cliente' in df_raw.columns:
            top_clients = df_raw['cliente'].value_counts().head(20).reset_index()
            top_clients.columns = ['Cliente', 'Transacciones']
            
            fig_cli = px.bar(top_clients, x="Cliente", y="Transacciones", title="Top Clientes por Frecuencia de Pedidos")
            st.plotly_chart(fig_cli, use_container_width=True)
        else:
            st.warning("Columna 'cliente' no encontrada en data raw.")
    else:
        st.warning("Data raw no disponible.")

# === 6. EXCEPCIONES ===
with tab_projects:
    st.markdown("### 🧹 Limpieza de Picos (Proyectos)")
    
    if not df_projects.empty:
        # KPI
        total_removed = df_projects['Qty'].sum()
        st.metric("Total Unidades Eliminadas (Ruido)", f"{int(total_removed):,}")
        
        # Chart
        st.subheader("Impacto por Més/Semana")
        # Ensure date
        df_projects['Fecha'] = pd.to_datetime(df_projects['Fecha'])
        proj_time = df_projects.groupby('Fecha')['Qty'].sum().reset_index()
        fig_proj = px.bar(proj_time, x="Fecha", y="Qty", title="Cronología de Proyectos Eliminados")
        st.plotly_chart(fig_proj, use_container_width=True)
        
        # Table
        st.dataframe(df_projects, use_container_width=True)
    else:
        st.success("No hay excepciones de ciclo de vida detectadas.")

# === 7. CALIDAD ===
with tab_quality:
    st.markdown("### ✅ Calidad de Datos")
    
    if not df_master.empty:
        # Check for zeroes
        zero_forecast = len(df_master[df_master['Forecast_Prom_Q'] == 0])
        zero_sigma = len(df_master[df_master['Sigma_Riesgo'] == 0])
        
        q1, q2 = st.columns(2)
        q1.metric("SKUs sin Forecast (Muertos)", zero_forecast)
        q2.metric("SKUs sin Variabilidad (Sigma=0)", zero_sigma)
        
        if zero_forecast > 0:
            st.subheader("⚠️ SKUs 'Muertos' o Nuevos (Forecast = 0)")
            st.dataframe(df_master[df_master['Forecast_Prom_Q'] == 0][['SKU', 'Clasificación', 'Stock_Actual']])
    else:
        st.error("Tabla maestra vacía.")
