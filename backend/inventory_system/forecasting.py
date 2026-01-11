
import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from typing import Dict, Any, List
import warnings
from backend.inventory_system import config

# Suppress warnings from statsmodels optimization
warnings.filterwarnings("ignore")

def forecast_sku_demand(df_sku: pd.DataFrame, periods: int = config.FORECAST_HORIZON_WEEKS) -> Dict[str, Any]:
    """
    Genera un forecast para UN solo SKU priorizando Holt-Winters.
    """
    
    # 1. Validación de Datos Mínimos
    if 'fecha' in df_sku.columns:
        data = df_sku.set_index('fecha')['cantidad']
    else:
        data = df_sku['cantidad']
    n_points = len(data)
    
    # Init outputs
    forecast = pd.Series()
    model_name = "Unknown"
    fitted_values = pd.Series()
    
    # 2. Logic: Force Exponential Smoothing
    try:
        # Heuristica: Necesitamos al menos 2 periodos para season
        seasonal_periods = 4 
        
        if n_points >= 2 * seasonal_periods:
             # INTENTO A: FULL HOLT-WINTERS (Trend + Season)
             model = ExponentialSmoothing(
                 data, 
                 seasonal_periods=seasonal_periods, 
                 trend='add', 
                 seasonal='add', 
                 damped_trend=True,
                 initialization_method='estimated'
             )
             model_name = "HoltWinters_Full"
             fit = model.fit(optimized=True)
             
        elif n_points >= 4:
             # INTENTO B: HOLT (Trend Only)
             model = ExponentialSmoothing(
                 data, 
                 trend='add', 
                 damped_trend=True, 
                 seasonal=None,
                 initialization_method='estimated'
             )
             model_name = "HoltWinters_Trend"
             fit = model.fit(optimized=True)
             
        else:
             # Si hay muy poquita data (<4), forzamos error para ir al fallback simple
             raise ValueError("Data insuficiente para HW/Holt")

        forecast = fit.forecast(periods)
        fitted_values = fit.fittedvalues
        
    except Exception as e:
        # FALLBACK 1: SIMPLE EXPONENTIAL SMOOTHING (Level Only)
        # Esto satisface "Solo HoltWinters" (es la base matemática)
        try:
            model = ExponentialSmoothing(data, trend=None, seasonal=None)
            fit = model.fit()
            forecast = fit.forecast(periods)
            fitted_values = fit.fittedvalues
            model_name = "ExponentialSmoothing_Simple"
        except Exception as e2:
            # FALLBACK 2: NAIVE (Ultimo valor)
            # Solo si todo lo demás falla (ej. data vacía o constante 0)
            last_val = data.iloc[-1] if n_points > 0 else 0
            
            # Crear indice futuro
            last_date = data.index[-1] if n_points > 0 else pd.Timestamp.now()
            forecast_index = pd.date_range(start=last_date, periods=periods+1, freq=config.TIME_FREQUENCY)[1:]
            
            forecast = pd.Series([last_val] * periods, index=forecast_index)
            fitted_values = data
            model_name = "Naive_LastValue_Fallback"

    # 3. Post-Processing: CLAMP NEGATIVES & ROUND UP (User Rule: Always Ceil)
    # "siempre redondea para arriba para predecir sus demandas"
    forecast = forecast.apply(lambda x: max(0, x))
    forecast = np.ceil(forecast)
    fitted_values = np.ceil(fitted_values)
    
    return {
        'model_type': model_name,
        'forecast': forecast, 
        'fitted_values': fitted_values
    }
