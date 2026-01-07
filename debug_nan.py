
import pandas as pd
import os

temp_file = "temp_inspect.xlsx"

try:
    xl = pd.ExcelFile(temp_file)
    for i, name in enumerate(xl.sheet_names):
        print(f"\n=== Sheet {i}: {name} ===")
        # Read without header to see raw data
        df_raw = pd.read_excel(temp_file, sheet_name=i, header=None)
        print("Raw first 10 rows:")
        print(df_raw.head(10).to_string())
        
        # Check for column with 'CIUDAD'
        for row_idx in range(len(df_raw)):
            row_vals = [str(x).upper().strip() for x in df_raw.iloc[row_idx].values]
            if 'CIUDAD' in row_vals:
                col_idx = row_vals.index('CIUDAD')
                print(f"DEBUG: Found 'CIUDAD' at row {row_idx}, col {col_idx}")
                
except Exception as e:
    print(f"Error: {e}")
