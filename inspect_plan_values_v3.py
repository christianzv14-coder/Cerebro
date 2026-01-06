
import pandas as pd
import os

# Use local temp copy
file_path = "temp_noviembre.xlsx"

try:
    df = pd.read_excel(file_path)
    # Strip columns
    df.columns = [c.strip() for c in df.columns]
    
    # Try to find the plan column
    possible_cols = ["Dist GPS", "L2", "Plan", "Distribuidor"]
    found_col = None
    for c in possible_cols:
        if c in df.columns:
            found_col = c
            break
            
    if found_col:
        print(f"\n--- Valores únicos en '{found_col}' ---")
        uniques = df[found_col].dropna().astype(str).unique().tolist()
        for u in sorted(uniques):
            print(f"'{u}'")
    else:
        print(f"\nNo se encontro columna de Plan candidata. Columnas: {df.columns.tolist()}")

except Exception as e:
    print(f"Error: {e}")
