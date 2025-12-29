
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
        print(f"Columns: {list(df.columns)}")
        if 'fecha' in df.columns:
            print(f"Unique Dates: {df['fecha'].unique()}")
        if 'tecnico_nombre' in df.columns:
            print(f"Technicians: {df['tecnico_nombre'].unique()}")
        if 'ticket_id' in df.columns:
            print(f"Ticket IDs ({len(df['ticket_id'].unique())} unique): {df['ticket_id'].tolist()}")
    except Exception as e:
        print(f"Error reading excel: {e}")
