
import pandas as pd
import numpy as np
import json
from datetime import datetime
from backend.inventory_system import config, preprocessing, forecasting, evaluation, policy, segmentation

def run_pipeline(df_activities: pd.DataFrame) -> dict:
    """
    Ejecuta el pipeline completo de inventario:
    Ingesta -> Preproc -> Segm -> Forecast -> Eval -> Policy -> Output
    
    Returns:
        Diccionario (JSON-ready) con resultados por SKU.
    """
    results = []
    
    print("1. [Pipeline] Preprocesando actividades...")
    df_demand = preprocessing.transform_activities_to_demand(df_activities)
    
    # Ejecutar Segmentacion ABC
    print("   [Pipeline] Calculando segmentación ABC...")
    abc_map = segmentation.segment_skus(df_demand)
    
    # Obtener lista única de SKUs
    skus = df_demand['sku'].unique()
    print(f"   -> SKUs detectados: {len(skus)}")
    
    for sku in skus:
        print(f"2. [Pipeline] Procesando SKU: {sku} (Clase {abc_map.get(sku, 'C')})")
        
        # Filtrar datos de este SKU y SETEAR INDICE FECHA para alineacion
        df_sku = df_demand[df_demand['sku'] == sku].sort_values('fecha').copy()
        df_sku = df_sku.set_index('fecha')
        
        # Ejecutar Forecast
        fc_result = forecasting.forecast_sku_demand(df_sku)
        
        # Evaluar Error
        # Usamos los residuos del entrenamiento como proxy del error futuro (in-sample)
        # En prod idealmente usaríamos TimeSeriesSplit, pero esto es aproximación operativa válida.
        metrics = evaluation.calculate_metrics(df_sku['cantidad'], fc_result['fitted_values'])
        
        # Calcular Política
        future_mean = fc_result['forecast'].mean()
        
        inv_policy = policy.calculate_inventory_policy(
            forecast_mean=future_mean,
            sigma_error=metrics['sigma']
        )
        
        # Estructurar Salida
        sku_output = {
            'sku': sku,
            'generated_at': datetime.now().isoformat(),
            'classification_abc': abc_map.get(sku, 'C'),  # NEW FIELD
            'model_used': fc_result['model_type'],
            'forecast_next_12_weeks': fc_result['forecast'].tolist(),
            'metrics': metrics,
            'inventory_policy': inv_policy,
            'status': 'OK' 
        }
        
        results.append(sku_output)
        
    return results

def run_simulation():
    """Genera datos dummy y corre el pipeline."""
    print("--- MODO SIMULACIÓN ---")
    
    # Generar datos dummy
    # 2 años de historia (104 semanas), 20 instalaciones/sem
    dates = pd.date_range(start="2024-01-01", periods=104, freq="W-MON")
    
    activities = []
    for d in dates:
        # Random noise
        qty = int(np.random.normal(20, 5)) 
        qty = max(0, qty)
        activities.append({'fecha': d, 'tipo_actividad': 'INSTALACION', 'cantidad_actividad': qty})
        
    df_dummy = pd.DataFrame(activities)
    print(f"Data Dummy creada: {len(df_dummy)} registros.")
    
    results = run_pipeline(df_dummy)
    
    # Guardar Output
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_FILE = os.path.join(BASE_DIR, 'outputs', 'inventory_output.json')
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f"Resultados guardados en {OUTPUT_FILE}")

if __name__ == "__main__":
    run_simulation()
