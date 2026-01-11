
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
FILE_SCENARIO_B = os.path.join(OUTPUT_DIR, 'Inventario_Escenario_2_SIN_PROYECTOS_V2.xlsx')

def run_pipeline_for_scenario(df_demand, scenario_name, output_file, outlier_log=None):
    print(f"\n🚀 EJECUTANDO ESCENARIO: {scenario_name}")
    print("-" * 50)
    
    results = []
    
    # 1. Segmentation
    print("   [1/4] Segmentando ABC...")
    # sku_volumes = df_demand.groupby('sku')['cantidad'].sum() -> No needed inside function
    abc_map = segmentation.segment_skus(df_demand)
    
    # 2. Forecasting & Policy
    print("   [2/4] Calculando Forecast & Stock...")
    unique_skus = df_demand['sku'].unique()
    
    for sku in unique_skus:
        df_sku = df_demand[df_demand['sku'] == sku].sort_values('fecha').copy()
        df_sku.set_index('fecha', inplace=True) # CRITICAL FIX: Align index with statsmodels output

        # Forecast
        forecast_result = forecasting.forecast_sku_demand(df_sku)
        
        # Eval
        # DEBUG: Ensure data alignment
        fit_vals = forecast_result['fitted_values']
        if fit_vals.empty:
             print(f"⚠️  WARNING: No Fitted Values for {sku}. Sigma will be 0.")
             
        metrics = evaluation.calculate_metrics(df_sku['cantidad'], fit_vals)
        
        # Policy
        # Policy espera SCALAR forecast_mean, pero calculamos policy para futura demanda agregada?
        # En pipeline.py, haciamos ROP para cada periodo. Aquí simplificaremos usando el promedio del forecast
        avg_forecast = forecast_result['forecast'].mean()
        
        pol = policy.calculate_inventory_policy(
            forecast_mean=avg_forecast,
            sigma_error=metrics['sigma'],
            lead_time_weeks=config.DEFAULT_LEAD_TIME_WEEKS
        )
        
        # Debug critical items
        if sku in ['Equipo GPS', 'ADAS', 'Cte motor']:
             print(f"   🔎 DEBUG {sku} [{scenario_name}]: Sigma={metrics['sigma']:.2f}, SS={pol['safety_stock']:.2f}, Model={forecast_result['model_type']}")

        # Result
        first_future_forecast = forecast_result['forecast'].iloc[0] if not forecast_result['forecast'].empty else 0
        
        res_entry = {
            'SKU': sku,
            'Clasificación': abc_map.get(sku, 'C'),
            'Modelo_Usado': forecast_result['model_type'], # Added User Request
            'Escenario': scenario_name,
            'Forecast_Prom_Q': round(avg_forecast, 2),
            'Sigma_Riesgo': round(metrics['sigma'], 2),
            'Stock_Seguridad': round(pol['safety_stock'], 2),
            'Punto_Reorden': round(pol['reorder_point'], 2),
            'Cantidad_A_Pedir': round(max(0, pol['reorder_point'] - 0), 2) # Assuming 0 stock
        }
        results.append(res_entry)
        
    # 3. Save to Excel
    print(f"   [3/4] Guardando {output_file}...")
    df_results = pd.DataFrame(results)
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_results.to_excel(writer, sheet_name='Reporte_Compras', index=False)
        
        if outlier_log is not None:
            outlier_log.to_excel(writer, sheet_name='Proyectos_Detectados', index=False)
            
    print("   ✅ Listo.")


def clean_data_remove_projects(df_demand, df_raw, threshold_sigma=1.2):
    print("\n🧹 LIMPIEZA DE DATOS (Detectando Proyectos...)")
    
    df_clean = df_demand.copy()
    outliers_list = []
    
    # Pre-process raw date for lookup
    df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
    
    for sku in df_clean['sku'].unique():
        mask = df_clean['sku'] == sku
        series = df_clean.loc[mask, 'cantidad']
        
        mean = series.mean()
        std = series.std()
        
        # Logic: Everything above Mean + 1.2 StdDev is considered a "Project Spike"
        limit = mean + (threshold_sigma * std)
        
        outlier_indices = series[series > limit].index
        
        if len(outlier_indices) > 0:
            # Log it
            for idx in outlier_indices:
                val = series[idx]
                date_label = df_clean.loc[idx, 'fecha']
                
                # FIX: Pandas W-MON labels "Week ENDING on Monday".
                # So "2025-03-10" covers "2025-03-04" to "2025-03-10".
                # My previous logic looked forward [date, date+6].
                # Correct logic: look BACKWARD [date-6, date].
                
                date_end = date_label + pd.Timedelta(days=1) # +1 to be safe inclusive
                date_start = date_label - pd.Timedelta(days=7) # Look back 7 days
                
                # Lookup Clients in Raw Data
                mask_raw = (df_raw['fecha'] >= date_start) & \
                           (df_raw['fecha'] <= date_end) & \
                           (df_raw['materiales_usados'].astype(str).str.contains(str(sku), regex=False))
                           
                relevant_raw = df_raw[mask_raw].copy()
                
                # PARSE QUANTITIES (Fix: Sum Quantity, don't count Rows)
                client_totals = {}
                
                for _, r_row in relevant_raw.iterrows():
                    cli = r_row.get('cliente', 'Unknown')
                    mat_str = str(r_row.get('materiales_usados', ''))
                    
                    # Parse "Item:Qty, Item2:Qty"
                    # Simple parse: split comma, find sku
                    qty_found = 0
                    pieces = mat_str.split(',')
                    for p in pieces:
                        if sku in p:
                            try:
                                # Format "Name:Qty"
                                part = p.split(':')[-1]
                                qty_found += float(part)
                            except:
                                pass
                                
                    client_totals[cli] = client_totals.get(cli, 0) + qty_found
                
                # Convert to Series for easy stats
                top_clients = pd.Series(client_totals).sort_values(ascending=False)
                
                # Statistical Significance Filter
                client_str = "0"
                
                if len(top_clients) > 0:
                    vals = top_clients.values
                    
                    if len(vals) == 1:
                        # Only one client exists -> They are the project
                        client_str = f"{top_clients.index[0]} ({int(vals[0])})"
                    else:
                        mean_v = np.mean(vals)
                        std_v = np.std(vals)
                        
                        # LOGIC: Must be greater than Mean + 0.5 * StdDev AND strictly > Mean 
                        threshold_cl = mean_v + (0.5 * std_v)
                        
                        significant_clients = top_clients[(top_clients > threshold_cl) & (top_clients > mean_v)]
                        
                        # DEBUG for User Verification
                        if sku == 'Equipo GPS' and len(significant_clients) > 0:
                            print(f"   ⚖️ DEBUG Attribution ({date_start.date()}): Mean={mean_v:.1f}, Std={std_v:.1f}, Threshold={threshold_cl:.1f}")
                            print(f"      Passed Filter: {significant_clients.to_dict()}")

                        if significant_clients.empty:
                            client_str = "0" # No one stands out significantly
                        else:
                            # Cap at Top 2
                            final_clients = significant_clients.head(2).to_dict()
                            client_str = ", ".join([f"{k} ({int(v)})" for k,v in final_clients.items()])

                outliers_list.append({
                    'SKU': sku,
                    'Fecha_Semana': date_start,
                    'Consumo_Real': val,
                    'Consumo_Base_Promedio': round(mean, 2),
                    'Exceso_Proyecto': val - mean,
                    'Clientes_Causantes': client_str 
                })
                
            # Replace with Mean (To simulate "Normal" week without project)
            # We don't delete to keep time continuity for HoltWinters
            df_clean.loc[outlier_indices, 'cantidad'] = mean
            
    return df_clean, pd.DataFrame(outliers_list)

def main():
    # 1. Load Raw Demand
    print("📂 Cargando Datos...")
    df_raw = pd.read_excel(DATA_FILE)
    df_demand = preprocessing.transform_activities_to_demand(df_raw)
    
    # 2. RUN SCENARIO A (WITH PROJECTS)
    run_pipeline_for_scenario(df_demand, "CON_PROYECTOS", FILE_SCENARIO_A)
    
    # 3. CLEAN DATA (Pass df_raw for attribution)
    df_demand_clean, outlier_log = clean_data_remove_projects(df_demand, df_raw)
    
    # 4. RUN SCENARIO B (WITHOUT PROJECTS)
    run_pipeline_for_scenario(df_demand_clean, "SIN_PROYECTOS", FILE_SCENARIO_B, outlier_log)
    
    print("\n✨ PROCESO TERMINADO. Dos archivos generados en /outputs.")


if __name__ == "__main__":
    main()
