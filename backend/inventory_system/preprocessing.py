
import pandas as pd
import numpy as np
import os
from typing import List, Dict
from backend.inventory_system import config

BOM_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'maestro_bom.xlsx')

def load_bom():
    """Carga el BOM desde Excel si existe, sino usa config."""
    if os.path.exists(BOM_FILE):
        print(f"   [BOM] Cargando maestro desde {BOM_FILE}")
        try:
            df_bom = pd.read_excel(BOM_FILE)
            # Convertir a dict: key=Actividad, val=[{sku, qty}]
            bom_map = {}
            for _, row in df_bom.iterrows():
                act = row['tipo_actividad']
                item = {'sku': row['sku'], 'qty': float(row['cantidad'])}
                if act not in bom_map:
                    bom_map[act] = []
                bom_map[act].append(item)
            return bom_map
        except Exception as e:
            print(f"   [ERROR] Falló carga de BOM externa: {e}")
            return config.DEFAULT_BOM
    else:
        return config.DEFAULT_BOM

def parse_material_string(mat_str: str) -> Dict[str, float]:
    """
    Parsea string 'SKU:Qty, SKU2:Qty2' -> {'SKU': Qty, ...}
    """
    if not isinstance(mat_str, str) or not mat_str.strip():
        return {}
    
    mapping = {}
    items = mat_str.split(',')
    for item in items:
        try:
            if ':' in item:
                sku, qty = item.split(':')
                mapping[sku.strip()] = float(qty)
        except:
            continue
    return mapping

def transform_activities_to_demand(df_activities: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte registro de actividades -> Demanda Histórica por SKU
    Soporta BOM Estático (maestro_bom) y Dinámico (columna materiales_usados).
    """
    # 1. Validación básica
    required_cols = ['fecha', 'tipo_actividad', 'cantidad_actividad']
    if not all(col in df_activities.columns for col in required_cols):
        raise ValueError(f"El DataFrame debe contener las columnas: {required_cols}")

    # Cargar BOM estático como fallback
    static_bom_map = load_bom() # Returns dict {Act: [{sku, qty}]}
    
    records = []
    
    # Check if we have dynamic BOM column
    has_dynamic_bom = 'materiales_usados' in df_activities.columns
    
    for _, row in df_activities.iterrows():
        fecha = row['fecha']
        actividad = row['tipo_actividad']
        cantidad = row['cantidad_actividad']
        
        # 1. Try Dynamic BOM first
        sku_consumption = {}
        used_dynamic = False
        
        if has_dynamic_bom:
            dynamic_map = parse_material_string(row['materiales_usados'])
            if dynamic_map:
                sku_consumption = dynamic_map
                used_dynamic = True
                
        # 2. Fallback to Static BOM
        if not used_dynamic:
            # El BOM estático original retorna una lista de dicts: [{'sku': 'X', 'qty': 1}, ...]
            # Necesitamos convertirlo a dict simple {sku: qty} para unificar logica
            static_products = static_bom_map.get(actividad, [])
            # Handle if static_bom_map returns config.DEFAULT_BOM structure (list of dicts per key)
            if isinstance(static_products, list):
                 sku_consumption = {p['sku']: p['qty'] for p in static_products}
            else:
                 sku_consumption = {}
        
        # 3. Explode
        if not sku_consumption:
             continue
             
        for sku, coef in sku_consumption.items():
            total_qty = cantidad * coef
            records.append({
                'fecha': fecha,
                'sku': sku,
                'cantidad': total_qty
            })
            
    if not records:
        print("⚠️ Warning: No se generaron consumos. Revisa si input_actividades coincide con BOM.")
        return pd.DataFrame(columns=['fecha', 'sku', 'cantidad'])
        
    df_consumo = pd.DataFrame(records)
    
    # 3. Conversión de Tipos
    df_consumo['fecha'] = pd.to_datetime(df_consumo['fecha'])
    
    # 4. Agregación Temporal
    # Usamos configuración de frecuencia
    freq = config.TIME_FREQUENCY
    
    df_agg = (
        df_consumo
        .groupby(['sku', pd.Grouper(key='fecha', freq=freq)])['cantidad']
        .sum()
        .reset_index()
        .sort_values(['sku', 'fecha'])
    )
    
    return df_agg
