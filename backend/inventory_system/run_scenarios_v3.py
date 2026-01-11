
import pandas as pd
import numpy as np
import os
import sys
from backend.inventory_system import preprocessing, segmentation, forecasting, evaluation, policy, config

# Setup Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'input_actividades.xlsx')
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')

FILE_SCENARIO_A = os.path.join(OUTPUT_DIR, 'Inventario_Escenario_1_CON_PROYECTOS.xlsx')
FILE_SCENARIO_C = os.path.join(OUTPUT_DIR, 'Inventario_Escenario_3_LIFECYCLE_V3.xlsx')

def run_pipeline_for_scenario(df_demand, scenario_name, output_file, outlier_log=None, current_stock_map=None):
    print(f"\n[RUNNING] EJECUTANDO ESCENARIO: {scenario_name}")
    print("-" * 50)
    
    results = []
    if current_stock_map is None:
        current_stock_map = {}
    
    # 1. Segmentation
    print("   [1/4] Segmentando ABC...")
    abc_map = segmentation.segment_skus(df_demand)
    
    # 2. Forecasting & Policy
    print("   [2/4] Calculando Forecast & Stock...")
    unique_skus = df_demand['sku'].unique()
    
    for sku in unique_skus:
        df_sku = df_demand[df_demand['sku'] == sku].sort_values('fecha').copy()
        df_sku.set_index('fecha', inplace=True)

        # Forecast
        forecast_result = forecasting.forecast_sku_demand(df_sku)
        
        # Eval
        fit_vals = forecast_result['fitted_values']
        metrics = evaluation.calculate_metrics(df_sku['cantidad'], fit_vals)
        
        # Policy
        # Round Inputs UP (Integer Safety)
        avg_forecast = float(np.ceil(forecast_result['forecast'].mean()))
        sigma_val = float(np.ceil(metrics['sigma']))
        
        pol = policy.calculate_inventory_policy(
            forecast_mean=avg_forecast,
            sigma_error=sigma_val,
            lead_time_weeks=config.DEFAULT_LEAD_TIME_WEEKS
        )
        
        # Determine Current Stock
        curr_stock = float(current_stock_map.get(sku, 0))
        
        # Round Outputs UP
        ss_val = float(np.ceil(pol['safety_stock']))
        rop_val = float(np.ceil(pol['reorder_point']))
        
        # Calc Order Qty = Max(0, ROP - Current_Stock)
        qty_order = float(np.ceil(max(0, rop_val - curr_stock)))
        
        res_entry = {
            'SKU': sku,
            'Clasificación': abc_map.get(sku, 'C'),
            'Modelo_Usado': forecast_result['model_type'],
            'Escenario': scenario_name,
            'Forecast_Prom_Q': int(avg_forecast),
            'Sigma_Riesgo': int(sigma_val),
            'Stock_Seguridad': int(ss_val),
            'Stock_Actual': int(curr_stock), # New Column
            'Punto_Reorden': int(rop_val),
            'Cantidad_A_Pedir': int(qty_order)
        }
        results.append(res_entry)
        
    # 3. Save
    print(f"   [3/4] Guardando {output_file}...")
    df_results = pd.DataFrame(results)
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_results.to_excel(writer, sheet_name='Reporte_Compras', index=False)
        if outlier_log is not None:
            outlier_log.to_excel(writer, sheet_name='Proyectos_Detectados', index=False)
            
    print("   [OK] Listo.")

def expand_raw_data(df_raw):
    """
    Expands raw activity rows into [Date, SKU, Client, Qty]
    Applies Global Filter for Service Activities.
    """
    expanded_rows = []
    # EXCLUSION LIST (Activity Type OR SKU Name)
    EXCLUDED_KEYWORDS = ['TECNICA', 'FALLIDA', 'SONDA', 'VISITA']

    for idx, row in df_raw.iterrows():
        # 1. FILTER by Activity Type (Robust)
        act_type = str(row.get('tipo_actividad', '')).strip().upper()
        if any(k in act_type for k in EXCLUDED_KEYWORDS):
            continue
            
        cli = str(row.get('cliente', 'Unknown')).strip()
        date = row['fecha']
        mat_str = str(row.get('materiales_usados', ''))
        
        pieces = mat_str.split(',')
        for p in pieces:
            if ':' in p:
                try:
                    sku_name, qty_str = p.split(':')
                    sku_clean = sku_name.strip()
                    
                    # 2. FILTER by SKU Name (The Real Fix)
                    # If the SKU itself is "V. Tecnica", drop it.
                    sku_upper = sku_clean.upper()
                    if any(k in sku_upper for k in EXCLUDED_KEYWORDS):
                        continue
                        
                    expanded_rows.append({
                        'fecha': date,
                        'sku': sku_clean,
                        'cliente': cli,
                        'cantidad': float(qty_str)
                    })
                except:
                    pass
    return pd.DataFrame(expanded_rows)

def aggregate_demand(df_expanded):
    """
    Aggregates expanded data into SKU Demand [Date, SKU, Qty]
    """
    if df_expanded.empty:
        return pd.DataFrame(columns=['fecha', 'sku', 'cantidad'])
        
    return df_expanded.groupby(['sku', pd.Grouper(key='fecha', freq='W-MON')])['cantidad'].sum().reset_index()

def clean_data_lifecycle(df_expanded):
    print("\n[CLEANING] LIMPIEZA DE DATOS (Detectando Ciclos > 1 Semana...)")
    
    # 2. Calculate Global Thresholds
    df_sku_weekly = df_expanded.groupby(['sku', pd.Grouper(key='fecha', freq='W-MON')])['cantidad'].sum().reset_index()
    sku_stats = df_sku_weekly.groupby('sku')['cantidad'].mean().to_dict()
    
    # 3. Detect Cycles
    projects_log = []
    
    # df_client_weekly = grouping by [SKU, Client, Week] 
    df_client_weekly = df_expanded.groupby(['sku', 'cliente', pd.Grouper(key='fecha', freq='W-MON')])['cantidad'].sum().reset_index()
    
    project_keys = set() 
    
    for sku in df_client_weekly['sku'].unique():
        threshold = sku_stats.get(sku, 0)
        df_sku = df_client_weekly[df_client_weekly['sku'] == sku]
        
        for cli in df_sku['cliente'].unique():
            timeline = df_sku[df_sku['cliente'] == cli].sort_values('fecha')
            current_sequence = []
            
            for _, row in timeline.iterrows():
                qty = row['cantidad']
                date = row['fecha']
                
                # LOGIC: > Threshold AND >= 3 units
                if qty > threshold and qty >= 3:
                     # In sequence
                    if current_sequence:
                        last_date = current_sequence[-1]['date']
                        if (date - last_date).days <= 7:
                            current_sequence.append({'date': date, 'qty': qty})
                        else:
                            # Break
                            if len(current_sequence) > 1:
                                for item in current_sequence:
                                    projects_log.append({
                                        'SKU': sku,
                                        'Cliente': cli,
                                        'Fecha': item['date'],
                                        'Qty': item['qty'],
                                        'Threshold': round(threshold, 2),
                                        'Duration_Weeks': len(current_sequence)
                                    })
                                    project_keys.update([(sku, cli, item['date']) for item in current_sequence])
                            current_sequence = [{'date': date, 'qty': qty}]
                    else:
                        current_sequence.append({'date': date, 'qty': qty})
                else:
                    if len(current_sequence) > 1:
                        for item in current_sequence:
                            projects_log.append({
                                'SKU': sku,
                                'Cliente': cli,
                                'Fecha': item['date'],
                                'Qty': item['qty'],
                                'Threshold': round(threshold, 2),
                                'Duration_Weeks': len(current_sequence)
                            })
                            project_keys.update([(sku, cli, item['date']) for item in current_sequence])
                    current_sequence = []
            
            if len(current_sequence) > 1:
                 for item in current_sequence:
                    projects_log.append({
                        'SKU': sku,
                        'Cliente': cli,
                        'Fecha': item['date'],
                        'Qty': item['qty'],
                        'Threshold': round(threshold, 2),
                        'Duration_Weeks': len(current_sequence)
                    })
                    project_keys.update([(sku, cli, item['date']) for item in current_sequence])

    # 4. Filter Projects from Demand
    df_total_demand = aggregate_demand(df_expanded)
    
    project_demand = pd.DataFrame(projects_log)
    if not project_demand.empty:
        project_agg = project_demand.groupby(['SKU', 'Fecha'])['Qty'].sum().reset_index()
        merged = pd.merge(df_total_demand, project_agg, left_on=['sku', 'fecha'], right_on=['SKU', 'Fecha'], how='left')
        merged['Qty'] = merged['Qty'].fillna(0)
        merged['clean_qty'] = merged['cantidad'] - merged['Qty']
        df_clean = merged[['fecha', 'sku', 'clean_qty']].rename(columns={'clean_qty': 'cantidad'})
    else:
        df_clean = df_total_demand[['fecha', 'sku', 'cantidad']]
        
    return df_clean, pd.DataFrame(projects_log)

def main():
    print("[LOADING] Cargando Datos...")
    df_raw = pd.read_excel(DATA_FILE)
    df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
    
    # 1. Expand Raw & Apply Global Filter
    df_expanded = expand_raw_data(df_raw)
    
    # LOAD STOCK SNAPSHOT (If exists)
    STOCK_FILE = os.path.join(BASE_DIR, 'data', 'input_stock.xlsx')
    stock_dict = {}
    if os.path.exists(STOCK_FILE):
        print(f"[STOCK] Cargando Stock Actual desde {STOCK_FILE}...")
        try:
            # Safe read not needed here mostly, but good practice
            df_stk = pd.read_excel(STOCK_FILE)
            # Clean SKUs
            df_stk['SKU'] = df_stk['SKU'].astype(str).str.strip()
            # Map sum (in case duplicates)
            stock_dict = df_stk.groupby('SKU')['Stock_Actual'].sum().to_dict()
            print(f"   - {len(stock_dict)} SKUs con stock cargado.")
        except Exception as e:
            print(f"[WARNING] Error cargando stock: {e}")
    else:
        print("[WARNING] No se encontró input_stock.xlsx (Asumiendo Stock 0)")

    # Helper to inject stock dict 
    def run_pipeline_with_stock(df, name, outfile, log=None):
        run_pipeline_for_scenario(df, name, outfile, log, current_stock_map=stock_dict)

    # 2. Scenario 1: Baseline
    df_baseline = aggregate_demand(df_expanded)
    FILE_SCENARIO_1 = os.path.join(OUTPUT_DIR, 'Inventario_Escenario_1_BASAL_LIMPIO.xlsx')
    run_pipeline_with_stock(df_baseline, "BASAL_LIMPIO", FILE_SCENARIO_1)
    
    # 3. Scenario 3: Lifecycle
    df_optimized, log = clean_data_lifecycle(df_expanded)
    FILE_SCENARIO_3 = os.path.join(OUTPUT_DIR, 'Inventario_Escenario_3_OPTIMIZADO_FINAL.xlsx')
    run_pipeline_with_stock(df_optimized, "OPTIMIZADO_FINAL", FILE_SCENARIO_3, log)
    
    print("\n[DONE] PROCESO TERMINADO. Dos escenarios generados.")

if __name__ == "__main__":
    main()
