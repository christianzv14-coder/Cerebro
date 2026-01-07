
import pandas as pd
import numpy as np

FILE = "temp_inspect.xlsx"
xl = pd.ExcelFile(FILE)

print(f"ALl SHEETS: {xl.sheet_names}")

for sheet_name in xl.sheet_names:
    print(f"\n===== SCANNING SHEET: {sheet_name} =====")
    df = xl.parse(sheet_name, header=None)
    print(f"Dimensions: {df.shape}")
    
    # Check for text like 'CIUDAD', 'TECNICO', etc.
    for r in range(min(50, len(df))):
        for c in range(min(50, len(df.columns))):
            val = df.iloc[r, c]
            if pd.isna(val): continue
            s_val = str(val).upper().strip()
            if any(k in s_val for k in ['CIUDAD', 'ENTEL', 'RABIE', 'BACKLOG', 'FALTAN', 'STATUS']):
                print(f"Marker '{s_val}' at R{r} C{c}")

    # Summarize numbers found in the grid
    numeric_data = []
    text_data = []
    for r in range(len(df)):
        for c in range(len(df.columns)):
            val = df.iloc[r, c]
            if pd.isna(val): continue
            if isinstance(val, (int, float)):
                if val > 0 and val < 500: # Typical demand range
                    numeric_data.append((r, c, val))
            elif isinstance(val, str):
                if len(val.strip()) > 3:
                    text_data.append((r, c, val.strip()))

    print(f"Total numeric cells (>0, <500): {len(numeric_data)}")
    if numeric_data:
        print("Sample numeric cells:", numeric_data[:10])
    
    print(f"First 10 text cells:", text_data[:10])
