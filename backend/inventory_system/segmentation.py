
import pandas as pd

def segment_skus(df_demand_agg: pd.DataFrame) -> dict:
    """
    Clasifica SKUs en A, B, C basado en volumen de consumo (Proxy de valor).
    
    Args:
        df_demand_agg: DataFrame con ['sku', 'fecha', 'cantidad'].
    
    Returns:
        Diccionario {sku: classification_char} ('A', 'B', 'C')
    """
    # 1. Calcular total consumo por SKU
    total_volume = df_demand_agg.groupby('sku')['cantidad'].sum().reset_index()
    total_volume = total_volume.sort_values('cantidad', ascending=False)
    
    # 2. Calcular acumulado
    total_system = total_volume['cantidad'].sum()
    if total_system == 0:
        return {sku: 'C' for sku in total_volume['sku']}
        
    total_volume['cumsum'] = total_volume['cantidad'].cumsum()
    total_volume['pct'] = total_volume['cumsum'] / total_system
    
    # 3. Asignar Clases (80/15/5)
    def classify(pct):
        if pct <= 0.80: return 'A'
        elif pct <= 0.95: return 'B'
        else: return 'C'
        
    total_volume['class'] = total_volume['pct'].apply(classify)
    
    return dict(zip(total_volume['sku'], total_volume['class']))
