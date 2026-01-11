
import pandas as pd
import os

import sys

def debug_adas():
    # Path Setup
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    INPUT_FILE = os.path.join(BASE_DIR, 'data', 'input_actividades.xlsx')
    BOM_FILE = os.path.join(BASE_DIR, 'data', 'maestro_bom.xlsx')
    OUTPUT_FILE = os.path.join(BASE_DIR, 'outputs', 'debug_adas.txt')

    # Redirigir output a fichero para evitar problemas de encoding consola
    sys.stdout = open(OUTPUT_FILE, 'w', encoding='utf-8')

    print("🔍 DIAGNÓSTICO DE 'ADAS' 🔍")
    
    # 1. Cargar Inputs
    df_act = pd.read_excel(INPUT_FILE)
    df_bom = pd.read_excel(BOM_FILE)
    
    print(f"\n1. TOTAL ACTIVIDADES (Input):")
    total_acts = df_act.groupby('tipo_actividad')['cantidad_actividad'].sum()
    print(total_acts)
    
    # 2. Revisar Receta BOM para ADAS
    print(f"\n2. RECETA BOM PARA 'ADAS':")
    # Filtrar donde SKU sea ADAS (o parecidos)
    # Normalizar strings por si acaso
    df_bom['sku_norm'] = df_bom['sku'].astype(str).str.upper().str.strip()
    adas_bom = df_bom[df_bom['sku_norm'].str.contains('ADAS')]
    
    if adas_bom.empty:
        print("❌ NO SE ENCONTRÓ 'ADAS' EN EL BOM.")
        return
        
    print(adas_bom[['tipo_actividad', 'sku', 'cantidad']])
    
    # 3. Calcular Consumo Teórico
    print(f"\n3. CÁLCULO DE CONSUMO HISTÓRICO:")
    total_adas = 0
    for _, row in adas_bom.iterrows():
        act_type = row['tipo_actividad']
        qty_per_act = row['cantidad']
        
        # Buscar cantidad total de esa actividad en el input
        # Asumiendo match exacto de string
        total_act_qty = df_act[df_act['tipo_actividad'] == act_type]['cantidad_actividad'].sum()
        
        subtotal = total_act_qty * qty_per_act
        print(f"   - Actividad '{act_type}': {total_act_qty} eventos * {qty_per_act} u/evento = {subtotal} ADAS")
        total_adas += subtotal
        
    print(f"\n   ------------------------------------------------")
    print(f"   TOTAL ADAS HISTÓRICO CALCULADO: {total_adas}")
    
    # Chequear rango de fechas
    df_act['fecha'] = pd.to_datetime(df_act['fecha'])
    weeks = (df_act['fecha'].max() - df_act['fecha'].min()).days / 7
    if weeks < 1: weeks = 1
    
    print(f"   Promedio Simple Semanal ({weeks:.1f} semanas): {total_adas / weeks:.2f}")

if __name__ == "__main__":
    debug_adas()
