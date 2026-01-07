
import pandas as pd
import os

temp_file = "temp_inspect.xlsx"

try:
    xl = pd.ExcelFile(temp_file)
    for i, name in enumerate(xl.sheet_names):
        print(f"\n=== Sheet {i}: {name} ===")
        df = pd.read_excel(temp_file, sheet_name=i)
        print("Columns:", df.columns.tolist())
        # Check rows for Santiago
        santiago = df[df.map(lambda x: 'SANTIAGO' in str(x).upper() if isinstance(x, str) else False).any(axis=1)]
        if not santiago.empty:
            print("Santiago Data:")
            print(santiago.to_string())
        else:
            print("No Santiago data found in this sheet.")

except Exception as e:
    print(f"Error: {e}")
