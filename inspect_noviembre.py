
import pandas as pd
import os

file_path = r"c:\Users\chzam\OneDrive\Desktop\cerebro-patio\Noviembre.xlsx"

try:
    df = pd.read_excel(file_path, nrows=5)
    print("Columns found:")
    print(df.columns.tolist())
    print("\nSample Data:")
    print(df.head())
    
    # Check for specific columns used in appp.py to see if they differ
    expected_cols = ["Fecha", "Cuenta", "Patente", "MB"]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        print(f"\nWARNING: Missing columns expected by appp.py: {missing}")
    else:
        print(f"\nSUCCESS: All core columns {expected_cols} found.")
        
except Exception as e:
    print(f"Error reading excel: {e}")
