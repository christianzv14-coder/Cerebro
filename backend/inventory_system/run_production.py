
import pandas as pd
import os
import sys
import json

# Add project root to path to allow absolute imports if run directly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.inventory_system.pipeline import run_pipeline

# Configuración de Rutas (Relativas a este script)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, 'data', 'input_actividades.xlsx')
OUTPUT_JSON = os.path.join(BASE_DIR, 'outputs', 'inventory_output_PROD.json')
OUTPUT_EXCEL = os.path.join(BASE_DIR, 'outputs', 'inventory_report_PROD.xlsx')

def main():
    print("🚀 INICIANDO SISTEMA DE INVENTARIO (MODO PRODUCCIÓN)")
    print(f"📂 Buscando archivo de entrada: {INPUT_FILE}...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ ERROR: No encontré el archivo '{INPUT_FILE}'.")
        print("   Por favor, crea ese Excel con las columnas: [fecha, tipo_actividad, cantidad_actividad]")
        sys.exit(1)
        
    try:
        # Cargar datos
        df = pd.read_excel(INPUT_FILE)
        print(f"✅ Archivo cargado. {len(df)} registros encontrados.")
        
        # Validar columnas
        req_cols = ['fecha', 'tipo_actividad', 'cantidad_actividad']
        if not all(col in df.columns for col in req_cols):
            print(f"❌ ERROR: Faltan columnas obligatorias. Se requiere: {req_cols}")
            print(f"   Encontrado: {list(df.columns)}")
            sys.exit(1)
            
        # Ejecutar Pipeline
        print("⚙️  Ejecutando Pipeline de Procesamiento...")
        results = run_pipeline(df)
        
        # Guardar Resultados JSON
        with open(OUTPUT_JSON, 'w') as f:
            json.dump(results, f, indent=4)
            
        # Generar Excel
        print("📊 Generando Reporte Excel...")
        excel_rows = []
        for r in results:
            row = {
                'SKU': r['sku'],
                'Clasificación ABC': r.get('classification_abc', 'C'),
                'Modelo': r['model_used'],
                'Forecast Promedio (12 sem)': sum(r['forecast_next_12_weeks']) / len(r['forecast_next_12_weeks']),
                'Error (Sigma)': r['metrics']['sigma'],
                'RMSE': r['metrics']['rmse'],
                'Stock de Seguridad': r['inventory_policy']['safety_stock'],
                'Punto de Reorden (ROP)': r['inventory_policy']['reorder_point'],
                'Lead Time (Sem)': r['inventory_policy']['lead_time_weeks'],
                'Status': r['status']
            }
            excel_rows.append(row)
            
        df_excel = pd.DataFrame(excel_rows)
        df_excel.to_excel(OUTPUT_EXCEL, index=False)
        
        print(f"✨ ÉXITO. Resultados guardados en:\n   JSON: {OUTPUT_JSON}\n   Excel: {OUTPUT_EXCEL}")
        
    except Exception as e:
        print(f"💥 ERROR CRÍTICO DURANTE LA EJECUCIÓN: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
