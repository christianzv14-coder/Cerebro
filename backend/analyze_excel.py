
import pandas as pd
import os

file_path = "plantilla_planificacion_v2.xlsx"
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
else:
    try:
        df = pd.read_excel(file_path)
        print("--- Excel Analysis ---")
        print(f"Shape: {df.shape}")
        if 'fecha' in df.columns:
            print(f"Date Column Type: {df['fecha'].dtype}")
            print(f"First 5 Raw Dates: {df['fecha'].head(5).tolist()}")
            # Attempt conversion to see what happens
            try:
                converted = pd.to_datetime(df['fecha'])
                print(f"Converted Dates (First 5): {converted.head(5).tolist()}")
            except Exception as e:
                print(f"Date Conversion Failed: {e}")
                
        if 'tecnico_nombre' in df.columns:
            print(f"Technicians: {df['tecnico_nombre'].unique()}")
    except Exception as e:
        print(f"Error reading excel: {e}")
