
import pandas as pd
import numpy as np
from typing import Dict

def calculate_metrics(y_true: pd.Series, y_pred: pd.Series) -> Dict[str, float]:
    """
    Calcula métricas de error entre la demanda real y la ajustada/predicha.
    
    Args:
        y_true: Serie real.
        y_pred: Serie predicha (fitted values).
    
    Returns:
        Diccionario con MAE, RMSE, Sigma (Desviación Std del Error).
    """
    
    # Alinear series por índice
    df = pd.DataFrame({'true': y_true, 'pred': y_pred}).dropna()
    
    if len(df) == 0:
        print(f"DEBUG: Empty intersection in evaluation. True len: {len(y_true)}, Pred len: {len(y_pred)}")
        if len(y_true) > 0:
            print(f"True Index Head: {y_true.index[:3]}")
        if len(y_pred) > 0:
            print(f"Pred Index Head: {y_pred.index[:3]}")
        return {'mae': 0.0, 'rmse': 0.0, 'sigma': 0.0}
        
    errors = df['true'] - df['pred']
    
    mae = np.mean(np.abs(errors))
    rmse = np.sqrt(np.mean(errors**2))
    sigma = np.std(errors)
    
    return {
        'mae': float(mae),
        'rmse': float(rmse),
        'sigma': float(sigma) # Critical for Safety Stock
    }
