
import pandas as pd
import os

def norm_city(x):
    return str(x).strip()

def explain_route():
    path = "data"
    
    # Load Params
    params = pd.read_excel(os.path.join(path, "parametros.xlsx"))
    param_dict = dict(zip(params['parametro'], params['valor']))
    bencina_factor = float(param_dict.get("precio_bencina_uf_km", 0.0))
    
    # Load Matrices for Santiago -> San Fernando
    origin = "Santiago"
    dest = "San Fernando"
    
    # Distance
    km_df = pd.read_excel(os.path.join(path, "matriz_distancia_km.xlsx"), index_col=0)
    km_df.index = km_df.index.map(norm_city)
    km_df.columns = km_df.columns.map(norm_city)
    dist = float(km_df.loc[origin, dest])
    
    # Peaje
    peaje_df = pd.read_excel(os.path.join(path, "matriz_peajes.xlsx"), index_col=0)
    peaje_df.index = peaje_df.index.map(norm_city)
    peaje_df.columns = peaje_df.columns.map(norm_city)
    peaje = float(peaje_df.loc[origin, dest])
    
    # Calculations
    fuel_cost = dist * bencina_factor
    total = fuel_cost + peaje
    
    print(f"--- DETAIL FOR {origin} -> {dest} ---")
    print(f"Distance (Matrix): {dist} km")
    print(f"Bencina Factor (Param): {bencina_factor} UF/km")
    print(f"Peaje (Matrix): {peaje} UF")
    print("-" * 30)
    print(f"Calc Fuel: {dist} * {bencina_factor} = {fuel_cost:.4f} UF")
    print(f"Calc Total: {fuel_cost:.4f} + {peaje:.4f} = {total:.4f} UF")

if __name__ == "__main__":
    explain_route()
