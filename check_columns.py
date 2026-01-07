
import pandas as pd
import os

temp_file = "temp_inspect.xlsx"

try:
    xl = pd.ExcelFile(temp_file)
    for i, name in enumerate(xl.sheet_names):
        print(f"\n--- Sheet {i}: {name} ---")
        df = pd.read_excel(temp_file, sheet_name=i)
        print("Columns:", df.columns.tolist())
        print(df.head(5))
except Exception as e:
    print(f"Error: {e}")
