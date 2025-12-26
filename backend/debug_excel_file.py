
import pandas as pd
import os
import sys

def inspect_generated():
    f = "backend/plantilla_planificacion_v2.xlsx"
    if not os.path.exists(f):
        print(f"File {f} does not exist.")
        return

    df = pd.read_excel(f)
    print(f"File: {f}")
    print(f"Rows: {len(df)}")
    print("Columns:", df.columns.tolist())
    
    # Check first few rows for Ticket ID
    print("First 5 rows Ticket IDs:")
    print(df['ticket_id'].head())
    
    # Check nulls
    nulls = df['ticket_id'].isna().sum()
    print(f"Null Ticket IDs: {nulls}")

if __name__ == "__main__":
    inspect_generated()
