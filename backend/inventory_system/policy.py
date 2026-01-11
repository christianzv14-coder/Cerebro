
import pandas as pd
import numpy as np
from backend.inventory_system import config

# Constant for Z-Score at 95% if scipy is missing, 
# but generally we can assume standard stack. 
# 90% = 1.28, 95% = 1.645, 99% = 2.33
Z_SCORES = {
    0.90: 1.28,
    0.95: 1.645,
    0.98: 2.05,
    0.99: 2.33
}

def calculate_inventory_policy(forecast_mean: float, sigma_error: float, lead_time_weeks: float = config.DEFAULT_LEAD_TIME_WEEKS) -> dict:
    """
    Calcula los parámetros de inventario (SS, ROP) para un SKU.
    
    Args:
        forecast_mean: Demanda promedio esperada por periodo (semana).
        sigma_error: Desviación estándar del error del forecast (incertidumbre).
        lead_time_weeks: Tiempo de reposición en semanas.
        
    Returns:
        Diccionario con políticas de inventario.
    """
    
    # 1. Obtener Z Score
    sl = config.SERVICE_LEVEL
    z_score = Z_SCORES.get(sl, 1.645) # Default 95%
    
    # 2. Calcular Stock de Seguridad (SS)
    # Fórmula: Z * Sigma_D * sqrt(LegacyTime)
    # Asumimos que sigma_error es por periodo (semana).
    # La incertidumbre crece con la raíz cuadrada del tiempo.
    safety_stock = z_score * sigma_error * np.sqrt(lead_time_weeks)
    
    # 3. Calcular Demanda durante Lead Time (DLT)
    demand_during_lead_time = forecast_mean * lead_time_weeks
    
    # 4. Calcular Punto de Reorden (ROP)
    # ROP = DLT + SS
    reorder_point = demand_during_lead_time + safety_stock
    
    return {
        'service_level': sl,
        'z_score': z_score,
        'safety_stock': float(safety_stock),
        'demand_lead_time': float(demand_during_lead_time),
        'reorder_point': float(reorder_point),
        'lead_time_weeks': lead_time_weeks
    }
