
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import shutil
import uuid
import numpy as np
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Cerebro Patio | Control Tower",
    page_icon="📡",
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
        try:
             return pd.read_excel(filepath, sheet_name=sheet_name, engine='openpyxl')
        except:
             return pd.DataFrame()
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

@st.cache_data
def load_and_prep_data():
    # 1. Load Master Data
    df_master = safe_read_excel(DATA_OPT, sheet_name='Reporte_Compras')
    # 3. Load Project Data
    df_projects = safe_read_excel(DATA_OPT, sheet_name='Proyectos_Detectados')
    # Standardize Project Columns (Output has Title Case)
    if not df_projects.empty:
        df_projects.rename(columns={
            'Fecha': 'fecha', 
            'SKU': 'sku', 
            'Cliente': 'cliente', 
            'Qty': 'cantidad'
        }, inplace=True)
        # Robustness: Strip keys to ensure perfect merge
        for col in ['sku', 'cliente']:
            if col in df_projects.columns:
                df_projects[col] = df_projects[col].astype(str).str.strip()
    
    # helper for expansion
    def expand_raw_data(df):
        expanded_rows = []
        for idx, row in df.iterrows():
            date = row.get('fecha')
            cli = str(row.get('cliente', 'Unknown')).strip()
            mat_str = str(row.get('materiales_usados', ''))
            
            for p in mat_str.split(','):
                if ':' in p:
                    try:
                        sku, qty = p.split(':')
                        # Filter bad SKUs
                        if any(x in sku.upper() for x in ['TECNICA','FALLIDA','SONDA']): continue
                        
                        expanded_rows.append({
                            'fecha': date,
                            'sku': sku.strip(), # Match column 'sku' used in viz
                            'cliente': cli,
                            'cantidad': float(qty),
                            'materiales_usados': sku.strip() # Mock for string filter compatibility
                        })
                    except: pass
        if not expanded_rows: return pd.DataFrame(columns=['fecha','sku','cliente','cantidad','materiales_usados'])
        return pd.DataFrame(expanded_rows)

    # 4. Load Raw & Expand
    df_raw_input = safe_read_excel(DATA_RAW)
    if not df_raw_input.empty:
        if 'fecha' in df_raw_input.columns:
            df_raw_input['fecha'] = pd.to_datetime(df_raw_input['fecha'])
        # EXPAND
        df_raw = expand_raw_data(df_raw_input)
        
        # TAG PROJECTS (New Logic - Robust Merge on Week)
        if not df_projects.empty and not df_raw.empty:
            df_projects['fecha'] = pd.to_datetime(df_projects['fecha'])
            df_projects['is_project'] = True
            
            # Create Merge Keys (Week-Monday Alignment)
            # The raw data might be daily. The projects are weekly logic.
            # Create Merge Keys (Week-Monday Alignment)
            df_raw['Semana_Merge'] = df_raw['fecha'] - pd.to_timedelta(df_raw['fecha'].dt.dayofweek, unit='d')
            df_projects['Semana_Merge'] = df_projects['fecha'] - pd.to_timedelta(df_projects['fecha'].dt.dayofweek, unit='d')

            # ZERO DUPLICATION TAGGING
            # Instead of merge, we use a boolean mask to prevent row inflation.
            df_raw['match_key'] = df_raw['Semana_Merge'].dt.strftime('%Y-%m-%d') + "_" + df_raw['sku'] + "_" + df_raw['cliente']
            proj_keys = set((df_projects['Semana_Merge'].dt.strftime('%Y-%m-%d') + "_" + df_projects['sku'] + "_" + df_projects['cliente']).unique())
            
            df_raw['is_project'] = df_raw['match_key'].isin(proj_keys)
            df_raw.drop(columns=['match_key'], inplace=True)
            df_raw['is_project'] = df_raw['is_project'].fillna(False)
            df_raw['Tipo'] = df_raw['is_project'].apply(lambda x: 'Proyecto (Pico)' if x else 'Regular')
            
            # Drop helper
            df_raw.drop(columns=['Semana_Merge'], inplace=True)
            
            # AMIGABLE DEBUG (Solo visible si hay mismatch)
            tagged_count = len(df_raw[df_raw['is_project']==True])
            # st.sidebar.metric("🔢 Eventos Picos Tagged", tagged_count)
        else:
            df_raw['Tipo'] = 'Regular'
            df_raw['is_project'] = False
    else:
        df_raw = pd.DataFrame()
    
    # --- CALCULATIONS ---
    if not df_master.empty:
        if 'Stock_Actual' not in df_master.columns: df_master['Stock_Actual'] = 0
            
        # WOS
        df_master['WOS'] = df_master.apply(
            lambda x: x['Stock_Actual'] / x['Forecast_Prom_Q'] if x['Forecast_Prom_Q'] > 0 else 999, axis=1
        )
        # Brecha ROP e Inicialización de Pedido
        df_master['Brecha_ROP'] = df_master['Stock_Actual'] - df_master['Punto_Reorden']
        df_master['Cantidad_A_Pedir'] = df_master.apply(lambda x: max(0, x['Punto_Reorden'] - x['Stock_Actual']), axis=1)
        
        # Status
        def get_status(row):
            if row['Stock_Actual'] < row['Punto_Reorden']: return "🔴 Bajo ROP"
            elif row['Stock_Actual'] < row['Punto_Reorden'] + row['Stock_Seguridad']: return "🟡 Alerta"
            return "🟢 OK"
        df_master['Estado_Stock'] = df_master.apply(get_status, axis=1)
        
        # Prioridad Score (Parametric-ready)
        # Risk (Under ROP) = 100 pts. ABC A = 50, B=30, C=10. WOS inv proportional.
        abc_w = {'A': 50, 'B': 30, 'C': 10}
        df_master['Prioridad_Score'] = df_master.apply(
            lambda x: (100 if x['Brecha_ROP'] < 0 else 0) + abc_w.get(x['Clasificación'], 0), axis=1
        )
    
    # --- GUARANTEE COLUMNS (Safety against KeyErrors) ---
    mandatory = {
        'Stock_Actual': 0, 'Punto_Reorden': 0, 'Stock_Seguridad': 0, 
        'Forecast_Prom_Q': 1, 'Sigma_Riesgo': 0, 'Cantidad_A_Pedir': 0, 
        'WOS': 999, 'Estado_Stock': 'OK', 'Prioridad_Score': 0
    }
    for col, default in mandatory.items():
        if col not in df_master.columns:
            df_master[col] = default
            
    return df_master, df_projects, df_raw

df_master, df_projects, df_raw = load_and_prep_data()

# --- SIDEBAR FILTERS ---
st.sidebar.title("📡 Control Tower")

# 1. Parámetros Globales (Editables - SIMULADOR)
st.sidebar.markdown("### ⚙️ Simulador de Políticas")

# BUTTON TO TRIGGER BACKEND UPDATE
import subprocess
import sys

if st.sidebar.button("🔄 Recalcular desde Excel (Backend)"):
    with st.spinner("⏳ Procesando nuevos datos... (Esto puede tardar unos segundos)"):
        try:
            # Prepare Environment with PYTHONPATH
            # This ensures 'backend' module is found
            current_env = os.environ.copy()
            # Add CWD (Cerebro root) to PYTHONPATH
            current_env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__)) # This gets backend/inventory_system dir... wait. 
            # We want the ROOT 'Cerebro'. 
            # __file__ is .../backend/inventory_system/dashboard.py
            # os.path.dirname -> .../backend/inventory_system
            # os.path.dirname -> .../backend
            # os.path.dirname -> .../Cerebro (Root)
            
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            current_env["PYTHONPATH"] = root_dir + os.pathsep + current_env.get("PYTHONPATH", "")

            # Use -m mode to run as module, preventing relative import issues
            # Command: python -m backend.inventory_system.run_scenarios_v3
            result = subprocess.run(
                [sys.executable, "-m", "backend.inventory_system.run_scenarios_v3"],
                cwd=root_dir, # Run from root
                env=current_env,
                capture_output=True,
                text=True,
                check=True
            )
            
            # If success
            st.success("✅ Datos actualizados correctamente.")
            st.cache_data.clear() # CLEAR CACHE to force reload
            st.rerun() # RELOAD APP
            
        except subprocess.CalledProcessError as e:
            st.error(f"❌ Error al ejecutar pipeline: {e.stderr}")
            # Debug info
            st.code(f"Output:\n{e.stdout}")
        except Exception as e:
            st.error(f"❌ Error desconocido: {e}")

lead_time_w = st.sidebar.number_input("Lead Time (Semanas)", 1, 10, 2, help="Tiempo de entrega del proveedor")
service_level_target = 0.95 # Could be slider too



# 2. Cliente (NEW)
st.sidebar.markdown("### 🔍 Filtros de Vista")
all_clients = ["Todos"]
if not df_raw.empty and 'cliente' in df_raw.columns:
    clients_found = sorted(df_raw['cliente'].astype(str).unique().tolist())
    all_clients = ["Todos"] + clients_found
    
selected_client = st.sidebar.selectbox("🏢 Cliente", all_clients)

# 3. Accesorio (MASTER FILTER)
# Filter List based on client
valid_skus = []
if not df_master.empty:
    valid_skus = sorted(df_master['SKU'].unique().tolist())

if selected_client != "Todos" and not df_raw.empty:
    # Get SKUs bought by this client
    client_skus = df_raw[df_raw['cliente'] == selected_client]['sku'].unique().tolist()
    # Intersect
    valid_skus = [s for s in valid_skus if s in client_skus]

all_skus = ["Todos"] + valid_skus
selected_sku = st.sidebar.selectbox("📦 Accesorio", all_skus)

# 4. Familia
# ... existing family code ...
if 'Familia' in df_master.columns:
    all_fams = ["Todas"] + sorted(df_master['Familia'].unique().tolist())
    selected_fam = st.sidebar.selectbox("📂 Familia", all_fams)
else:
    selected_fam = "Todas"

# 4. ABC
selected_abc = st.sidebar.multiselect("Clasificación ABC", ['A', 'B', 'C'], default=['A', 'B', 'C'])

# 5. Projects
show_projects = st.sidebar.checkbox("🏗️ Ver Proyectos (Picos)", value=False, help="Si se activa, los gráficos muestran los picos de demanda debidos a proyectos especiales.")

# --- DYNAMIC RECALCUTATION (THE GAME CHANGER) ---
if not df_master.empty:
    df_viz = df_master.copy()
    
    # 0. RECALCULATE BASE METRICS (Forecast & Sigma) FROM RAW DATA
    if not df_raw.empty and 'sku' in df_raw.columns:
        # Pre-calculate Weekly Demand
        raw_w = df_raw.copy()
        raw_w['Week'] = raw_w['fecha'] - pd.to_timedelta(raw_w['fecha'].dt.dayofweek, unit='d')
        df_weekly_all = raw_w.groupby(['sku', 'Week'])['cantidad'].sum().reset_index()
        
        # 1. Calc CLEAN StdDev (Baseline) -> Represents the Excel State
        # We need this to match the Excel exactly when projects are hidden.
        # But wait, df_viz ALREADY has the Excel Sigma.
        # So we just need to know the RATIO of Dirty vs Clean volatility.
        
        if show_projects:
            # SCENARIO: DIRTY (Projects Included)
            # Logic: New_Sigma = Excel_Sigma * (Std_Dirty / Std_Clean)
            
            # A. Std Clean
            clean_sku_list = df_raw[df_raw['is_project']==False]
            clean_w = clean_sku_list.copy()
            clean_w['Week'] = clean_w['fecha'] - pd.to_timedelta(clean_w['fecha'].dt.dayofweek, unit='d')
            std_clean = clean_w.groupby(['sku', 'Week'])['cantidad'].sum().groupby('sku').std()
            
            # B. Std Dirty
            std_dirty = df_weekly_all.groupby('sku')['cantidad'].std()
            
            # C. Mean Dirty (Forecast Update) - This CAN be direct mean
            mean_dirty = df_weekly_all.groupby('sku')['cantidad'].mean()
            
            # Merge to viz
            scaler = pd.DataFrame({'std_clean': std_clean, 'std_dirty': std_dirty, 'new_forecast': mean_dirty})
            # Handle zeros
            scaler['ratio'] = scaler['std_dirty'] / scaler['std_clean'].replace(0, 1)
            scaler['ratio'] = scaler['ratio'].fillna(1.0)
            
            df_viz = pd.merge(df_viz, scaler, left_on='SKU', right_index=True, how='left')
            
            # Apply Scaling
            # If ratio < 1 (impossible usually), clip to 1. Projects shouldn't reduce risk.
            df_viz['ratio'] = df_viz['ratio'].apply(lambda x: max(1.0, x))
            
            df_viz['Sigma_Riesgo'] = np.ceil(df_viz['Sigma_Riesgo'] * df_viz['ratio'])
            df_viz['Forecast_Prom_Q'] = np.ceil(df_viz['new_forecast'].fillna(df_viz['Forecast_Prom_Q']))
            
        else:
            # SCENARIO: CLEAN (Projects Hidden)
            # TRUST THE EXCEL. The Excel was optimized on Clean Data.
            # Do NOTHING. df_viz already has the correct Clean Sigma (17).
            pass
     
        # Safety rounding just in case
        df_viz['Forecast_Prom_Q'] = np.ceil(df_viz['Forecast_Prom_Q'])
        df_viz['Sigma_Riesgo'] = np.ceil(df_viz['Sigma_Riesgo'])

    # RECALCULATE POLICY BASED ON SLIDER INPUT & DYNAMIC METRICS
    # ROP = Forecast * LeadTime + SafetyStock
    # SafetyStock = Z * Sigma * sqrt(LeadTime)
    from scipy.stats import norm
    z_score = norm.ppf(service_level_target)
    
    # Vectorized Recalc
    # SS = Z * Sigma * sqrt(L)
    df_viz['Stock_Seguridad'] = np.ceil(z_score * df_viz['Sigma_Riesgo'] * np.sqrt(lead_time_w))
    # ROP = (Mean * L) + SS
    df_viz['Punto_Reorden'] = np.ceil((df_viz['Forecast_Prom_Q'] * lead_time_w) + df_viz['Stock_Seguridad'])
    
    # Status Update
    df_viz['Brecha_ROP'] = df_viz['Stock_Actual'] - df_viz['Punto_Reorden']
    
    def get_status_dynamic(row):
        if row['Stock_Actual'] < row['Punto_Reorden']: return "🔴 Bajo ROP"
        elif row['Stock_Actual'] < row['Punto_Reorden'] + row['Stock_Seguridad']: return "🟡 Alerta"
        return "🟢 OK"
    
    df_viz['Estado_Stock'] = df_viz.apply(get_status_dynamic, axis=1)
    
    # Recalc Qty to Order
    # Q = Max(0, ROP - Current)
    df_viz['Cantidad_A_Pedir'] = df_viz.apply(lambda x: max(0, x['Punto_Reorden'] - x['Stock_Actual']), axis=1)
    df_viz['WOS'] = df_viz.apply(lambda x: x['Stock_Actual'] / x['Forecast_Prom_Q'] if x['Forecast_Prom_Q'] > 0 else 999, axis=1)

    # --- FILTER LOGIC ---
    # Hierarchy: Client > SKU > Family > ABC
    
    # 0. Client Filter
    if selected_client != "Todos" and not df_raw.empty:
         # Dynamic Filter: Only SKUs bought by this client IN THE SELECTED VIEW (Project/Regular)
         # Using raw_filter from earlier might be better, but let's stick to simple
         client_base = df_raw[df_raw['cliente'] == selected_client]
         if not show_projects:
             client_base = client_base[client_base['is_project'] == False]
         client_skus = set(client_base['sku'].unique())
         df_viz = df_viz[df_viz['SKU'].isin(client_skus)]

    # 1. SKU Filter
    if selected_sku != "Todos":
        df_viz = df_viz[df_viz['SKU'] == selected_sku]
    else:
        # 2. Family Filter
        if 'Familia' in df_viz.columns and selected_fam != "Todas":
            df_viz = df_viz[df_viz['Familia'] == selected_fam]
        
        # 3. ABC Filter
        df_viz = df_viz[df_viz['Clasificación'].isin(selected_abc)]
else:
    df_viz = pd.DataFrame()

# Horizon only for viz
horizon_w = 12

# --- PAGES ---
page_names = ["🏠 Home: Control Tower", "🔭 Accesorio 360°", "🛒 Reposición", "🔮 Forecast", "🏢 Clientes", "🏗️ Proyectos"]
# Create tabs explicitly
t_home, t_360, t_repo, t_fcst, t_cli, t_proj = st.tabs(page_names)

# === 1. HOME: CONTROL TOWER ===
with t_home:
    st.markdown("### Panorama del Portafolio")
    
    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    if not df_viz.empty:
        risk_skus = len(df_viz[df_viz['Estado_Stock'] == "🔴 Bajo ROP"])
        k1.metric("🔴 En Riesgo (Bajo ROP)", risk_skus)
        
        buy_vol = df_viz['Cantidad_A_Pedir'].sum()
        k2.metric("🛒 Necesidad de Compra", f"{int(buy_vol):,}")
        
        avg_wos = df_viz[df_viz['WOS'] < 999]['WOS'].median()
        k3.metric("📅 Cobertura Típica", f"{avg_wos:.1f} sem")
        
        proj_removed = df_projects['cantidad'].sum() if not df_projects.empty else 0
        k4.metric("🧹 Ruido Eliminado", f"{int(proj_removed):,}")

    # Visuals
    c_bub, c_cal = st.columns([2, 1])
    
    with c_bub:
        st.subheader("📡 Radar de Riesgo (Cobertura vs Volatilidad)")
        if not df_viz.empty:
            # Bubble Chart
            fig_bub = px.scatter(
                df_viz[df_viz['WOS'] < 52],
                x="WOS", y="Sigma_Riesgo",
                size="Forecast_Prom_Q", color="Clasificación",
                hover_name="SKU",
                title="Tamaño burbuja = Velocidad de Venta",
                color_discrete_map={'A': '#EF553B', 'B': '#636EFA', 'C': '#00CC96'}
            )
            fig_bub.add_vrect(x0=0, x1=lead_time_w, fillcolor="red", opacity=0.1, annotation_text="Danger Zone")
            st.plotly_chart(fig_bub, use_container_width=True)
            
    with c_cal:
        st.subheader("🔥 Top 10 Prioridades")
        if not df_viz.empty:
            top_prio = df_viz.sort_values('Prioridad_Score', ascending=False).head(10)
            st.dataframe(
                top_prio[['SKU', 'Estado_Stock', 'Cantidad_A_Pedir']],
                use_container_width=True,
                hide_index=True
            )

# === 2. ACCESORIO 360 ===
with t_360:
    st.markdown("### 🔭 Visión Profunda por Accesorio")
    
    # Selection Logic
    if not df_viz.empty:
        available_skus = sorted(df_viz['SKU'].unique())
        
        # Logic: If specific global selection, lock to it. If Todos, show Select placeholder.
        if selected_sku != "Todos":
             # Force list to be just this one or keep context? 
             # Better: Keep full context allowed by Filters, but default to selection.
             # Wait, df_viz IS filtered by selected_sku so available_skus has len=1.
             # Loophole: If user picked 'ADAS' in sidebar, df_viz only has 'ADAS'.
             # To let them switch inside 360, we need 'available_skus' from df_master (filtered by ABC/Fam).
             
             # Let's fix the "Locked" issue first:
             # If we want to allow switching in 360 even if global is specific, we rely on df_viz being the constraint.
             # If users want to switch, they select "Todos" in sidebar.
             
             idx = 0
             target_360 = st.selectbox("🎯 Accesorio Seleccionado", available_skus, index=0, key="sku_360_locked", disabled=True)
             st.caption("ℹ️ Para cambiar de accesorio, usa el filtro 'Accesorio' en la barra lateral o selecciona 'Todos'.")
             
        else:
            # Global is Everyone. Show full list.
            # Add Placeholder
            final_options = ["(Seleccionar...)"] + available_skus
            target_360 = st.selectbox(
                f"🎯 Buscar Accesorio ({len(available_skus)} disponibles)", 
                final_options,
                index=0,
                key="sku_360_open"
            )
            
            if target_360 == "(Seleccionar...)":
                target_360 = None
                st.info("👈 Selecciona un accesorio del menú de arriba para ver su análisis 360°.")
                st.markdown("### 🔭 ¿Qué verás aquí?")
                k1, k2, k3 = st.columns(3)
                k1.metric("Stock y ROP", "---")
                k2.metric("Proyección Futura", "---")
                k3.metric("Historia de Demanda", "---")

    else:
        target_360 = None
        
    if target_360:
        # CRITICAL FIX: Use df_viz (Dynamic) instead of df_master (Static)
        # This ensures the 360 view reflects the "Project Toggle" and Recalculations.
        # Fallback to df_master if SKU not in viz (unlikely)
        if not df_viz.empty and target_360 in df_viz['SKU'].values:
            row = df_viz[df_viz['SKU'] == target_360].iloc[0]
        else:
            row = df_master[df_master['SKU'] == target_360].iloc[0]
            # Safety inject if missing
            if 'Cantidad_A_Pedir' not in row:
                row['Cantidad_A_Pedir'] = max(0, row['Punto_Reorden'] - row['Stock_Actual'])
        
        # 1. Snapshot Header
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("SKU", row['SKU'])
        s2.metric("Stock Actual", f"{int(row['Stock_Actual'])}")
        s3.metric("Punto Reorden (ROP)", f"{int(row['Punto_Reorden'])}")
        s4.metric("Stock Seguridad", f"{int(row['Stock_Seguridad'])}")
        
        # DEBUG S5: Total Demand Integrity
        total_d = df_raw[df_raw['sku'] == target_360]['cantidad'].sum()
        s5.metric("Demanda Hist. Total", f"{int(total_d)}", help="Suma total de todas las cantidades en el archivo de entrada para este SKU.")
        
        st.divider()
        
        # 1. UNIFIED TIMELINE (The "Big Picture")
        st.subheader("🌐 Línea de Tiempo Unificada: Historia + Proyección")
        
        # Controls for Timeline
        col_ctrl, _ = st.columns([1, 3])
        with col_ctrl:
            default_start = datetime(2025, 1, 1)
            date_range_start = st.date_input("📅 Desde", value=default_start)

        # Prepare Data
        # A. History (Past Demand)
        hist_dates = []
        hist_vals = []
        hist_df_viz = pd.DataFrame()
        
        if not df_raw.empty and 'sku' in df_raw.columns:
            raw_sku = df_raw[df_raw['sku'] == target_360].copy()
            if not raw_sku.empty:
                # FILTER LOGIC:
                
                # 0. Client Filter
                if selected_client != "Todos":
                    raw_sku = raw_sku[raw_sku['cliente'] == selected_client]

                # 1. Project Filter
                if not show_projects:
                    # Filter out projects
                    raw_sku = raw_sku[raw_sku['is_project'] == False]
                
                # Verify columns for grouping
                # We group by Week and Type to support stacking
                # If aggregation loses Type, we must group by Type too.
                # However, resample expects datetime index.
                # Let's use groupby with Grouper.
                
                # Filter by Date
                start_date_ts = pd.Timestamp(date_range_start)
                raw_sku = raw_sku[raw_sku['fecha'] >= start_date_ts]
                
                if show_projects:
                    # Stacked Data preparation: Aggregate FIRST to avoid any row-inflation from merge
                    hist_df_viz = raw_sku.groupby([pd.Grouper(key='fecha', freq='W-MON'), 'Tipo'])['cantidad'].sum().reset_index()
                else:
                    # Simple (Regular only): Aggregate FIRST
                    hist_df_viz = raw_sku.groupby([pd.Grouper(key='fecha', freq='W-MON')])['cantidad'].sum().reset_index()
                    hist_df_viz['Tipo'] = 'Regular' 
                
                if not hist_df_viz.empty:
                    hist_dates = hist_df_viz['fecha'].tolist() # Approx for line alignment
                    # Note: hist_vals not used directly in Stacked mode, relying on DF

        # B. Future (Projected Inventory)
        # ... (Calc remains same) ...
        dates = [datetime.today() + timedelta(weeks=i) for i in range(horizon_w + 1)]
        # ... code continues ...
        # B. Future (Projected Inventory)
        horizon_w = 26 # 6 Months Extended
        dates = [datetime.today() + timedelta(weeks=i) for i in range(horizon_w + 1)]
        
        fcst = row['Forecast_Prom_Q']
        current = row['Stock_Actual']
        rop = row['Punto_Reorden']
        ss = row['Stock_Seguridad']
        # Sigma Viz
        sigma = row['Sigma_Riesgo'] if 'Sigma_Riesgo' in row else 0
        
        proj_inv = []
        proj_upper = []
        proj_lower = []
        
        sim_stock = current
        
        # Reset Sim State
        order_placed = False
        arrival_date = None
        events = []
        
        for d in dates:
            proj_inv.append(sim_stock)
            proj_upper.append(sim_stock + sigma)
            proj_lower.append(max(0, sim_stock - sigma))

            # REPLENISHMENT LOGIC:
            if sim_stock <= rop and not order_placed:
                suggested_qty = row['Cantidad_A_Pedir'] if 'Cantidad_A_Pedir' in row else 0
                order_qty = max(suggested_qty, (rop + ss + (lead_time_w * fcst)) - sim_stock)
                
                if order_qty > 0:
                    events.append({'date': d, 'type': 'Orden', 'qty': order_qty})
                    order_placed = True
                    order_qty_at_time = order_qty 
                    arrival_date = d + timedelta(weeks=lead_time_w)  
            
            if arrival_date and d >= arrival_date:
                sim_stock += order_qty_at_time
                events.append({'date': d, 'type': 'Llegada', 'qty': order_qty_at_time})
                arrival_date = None
                order_placed = False
            
            sim_stock = max(0, sim_stock - fcst)
            
        # Draw Plotly Figure
        fig_dual = go.Figure()
        
        # Trace 1: History Bars (Stacked or Simple)
        if not hist_df_viz.empty:
            if show_projects:
                 # We need to iterate types to create stacks manually for go.Bar or use px and extract traces
                 # Mixing px and go is messy. Let's do manual traces.
                 for t_type, color in [('Regular', 'lightgray'), ('Proyecto (Pico)', '#FF6666')]:
                     subset = hist_df_viz[hist_df_viz['Tipo'] == t_type]
                     if not subset.empty:
                         fig_dual.add_trace(go.Bar(
                            x=subset['fecha'], y=subset['cantidad'],
                            name=f'Demanda {t_type}',
                            marker_color=color,
                            opacity=0.7,
                            yaxis='y2'
                         ))
                 fig_dual.update_layout(barmode='stack')
            else:
                 fig_dual.add_trace(go.Bar(
                    x=hist_df_viz['fecha'], y=hist_df_viz['cantidad'], 
                    name='Demanda Regular', 
                    marker_color='lightgray',
                    opacity=0.6,
                    yaxis='y2'
                ))
        
        # Trace 2: Inventory Projection
        # 2.1 Variability Cloud (Confidence Interval)
        fig_dual.add_trace(go.Scatter(
            x=dates + dates[::-1], # Upper then Lower reversed
            y=proj_upper + proj_lower[::-1],
            fill='toself',
            fillcolor='rgba(99, 110, 250, 0.2)', # Transparent Blue
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            showlegend=True,
            name='Variabilidad (Sigma)'
        ))

        # 2.2 Main Projection Line
        fig_dual.add_trace(go.Scatter(
            x=dates, y=proj_inv, 
            name='Inventario Futuro', 
            mode='lines+markers', 
            line=dict(color='#636EFA', width=4),
            # fill='tozeroy', # Removed to avoid clutter with cloud
        ))
        
        # ... (References/Events same) ...
        # Reference Lines
        fig_dual.add_hline(y=rop, line_dash="dash", line_color="orange", annotation_text="ROP")
        fig_dual.add_hline(y=ss, line_dash="dot", line_color="red", annotation_text="Safety Stock")
        
        for e in events:
            fig_dual.add_annotation(
                x=e['date'], y=rop if e['type']=='Orden' else (rop+e['qty']),
                text=f"{e['type']} {int(e['qty'])}",
                showarrow=True, arrowhead=2, ax=0, ay=-40,
                bgcolor="yellow" if e['type']=='Orden' else "#90EE90",
                font=dict(color="black", size=10) # FIX: Black text for readability
            )

        # Layout
        title_suffix = " (CON Picos)" if show_projects else " (LIMPIO)"
        fig_dual.update_layout(
            title=f"Histórico{title_suffix} vs Futuro - {target_360}",
            xaxis_title="Tiempo",
            xaxis=dict(
                tickformat="%b %Y",
                dtick="M1" # Force monthly ticks
            ),
            yaxis_title="Inventario (Unidades)",
            yaxis2=dict(
                title="Demanda Semanal",
                overlaying='y',
                side='right',
                showgrid=False
            ),
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1)
        )
        
        # Add "Today" line (Safe Manual Shape)
        current_date_ts = pd.Timestamp.today()
        fig_dual.add_shape(
            type="line", x0=current_date_ts, y0=0, x1=current_date_ts, y1=1,
            yref="paper", line=dict(color="black", width=2)
        )
        fig_dual.add_annotation(
            x=current_date_ts, y=1, yref="paper", text="HOY", showarrow=False,
            yshift=10, font=dict(color="black", weight="bold")
        )
        
        st.plotly_chart(fig_dual, use_container_width=True)

# ... (Existing Tabs) ...

# === 6. PROYECTOS ===
with t_proj:
    st.markdown("### 🏗️ Gestión de Proyectos Detectados")
    st.markdown("Esta pestaña detalla los **picos de demanda** identificados como 'No Recurrentes'.")
    
    if not df_projects.empty:
        # Metrics
        kp1, kp2, kp3 = st.columns(3)
        kp1.metric("Eventos Detectados", len(df_projects))
        kp2.metric("Volumen Total Excluido", f"{int(df_projects['cantidad'].sum()):,} u")
        unique_proj_skus = df_projects['sku'].nunique()
        kp3.metric("Materiales Afectados", unique_proj_skus)
        
        st.divider()
        
        c_p1, c_p2 = st.columns(2)
        
        with c_p1:
            st.subheader("📋 Log de Excepciones")
            st.dataframe(df_projects, use_container_width=True)
            
        with c_p2:
            st.subheader("📊 Impacto por Cliente")
            if 'cliente' in df_projects.columns:
                fig_proj = px.bar(
                    df_projects.groupby('cliente')['cantidad'].sum().reset_index().sort_values('cantidad', ascending=False).head(10),
                    x='cliente', y='cantidad',
                    title="Top Clientes Generadores de Proyectos"
                )
                st.plotly_chart(fig_proj, use_container_width=True)
    else:
        st.info("✅ No se han detectado proyectos (outliers) en la carga actual.")

        # 2. Timeline Future Projection (Keep detailed/separated if needed, or remove since merged)
        # st.subheader("🔮 Detalles de Proyección") ... (Removing purely redundant chart, keeping only logic)


# === 3. REPOSICION ===
with t_repo:
    st.markdown("### 🛒 Plan de Reposición")
    
    col_kpi, col_table = st.columns([1,3])
    
    with col_kpi:
        st.metric("Total a Pedir", f"{int(df_viz['Cantidad_A_Pedir'].sum()):,} u")
        if st.checkbox("Ver solo Críticos (Bajo ROP)", value=True):
            df_repo = df_viz[df_viz['Estado_Stock'] == "🔴 Bajo ROP"]
        else:
            df_repo = df_viz[df_viz['Cantidad_A_Pedir'] > 0]
            
    with col_table:
        st.dataframe(
            df_repo[['SKU', 'Clasificación', 'Stock_Actual', 'Punto_Reorden', 'Cantidad_A_Pedir', 'WOS']],
            use_container_width=True,
            column_config={
                "Cantidad_A_Pedir": st.column_config.ProgressColumn("Q Sugerida", format="%d", min_value=0, max_value=int(df_viz['Cantidad_A_Pedir'].max() if not df_viz.empty else 100)),
                "WOS": st.column_config.NumberColumn("Cobertura", format="%.1f")
            }
        )

# === 4. FORECAST ===
with t_fcst:
    st.markdown("### 🔮 Salud del Pronóstico")
    st.info("Comparación de volatilidad (Sigma) vs Pronóstico promedio.")
    
    df_fcst = df_viz.copy()
    df_fcst['CV'] = df_fcst['Sigma_Riesgo'] / df_fcst['Forecast_Prom_Q']
    
    fig_cv = px.bar(
        df_fcst.sort_values('CV', ascending=False).head(20),
        x="SKU", y="CV", color="Clasificación",
        title="Top 20 SKUs más Volátiles (Mayor Incertidumbre)",
        labels={"CV": "Coeficiente Variación (Sigma/Media)"}
    )
    st.plotly_chart(fig_cv, use_container_width=True)

# === 5. CLIENTES ===
with t_cli:
    st.markdown("### 🏢 Concentración")
    if not df_raw.empty and 'sku' in df_raw.columns:
        # Filter raw by SKU list
        target_skus = df_viz['SKU'].unique()
        raw_filt = df_raw[df_raw['sku'].isin(target_skus)]
        
        # APPLY PROJECT FILTER
        if not show_projects:
             raw_filt = raw_filt[raw_filt['is_project'] == False]
        
        if not raw_filt.empty and 'cliente' in raw_filt.columns:
            top_cli = raw_filt['cliente'].value_counts().head(15).reset_index()
            top_cli.columns = ['Cliente', 'Pedidos'] # Counting rows is roughly orders if expanded
            # Actually strictly it is line items. 
            # If we want volume, sum quantity
            top_vol = raw_filt.groupby('cliente')['cantidad'].sum().reset_index().sort_values('cantidad', ascending=False).head(15)
            
            fig_cli = px.bar(top_vol, x="cliente", y="cantidad", title="Top Clientes (Volumen Total)")
            st.plotly_chart(fig_cli, use_container_width=True)
    else:
        st.warning("Sin datos de clientes.")
