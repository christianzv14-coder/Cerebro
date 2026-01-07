
import pandas as pd
from datetime import datetime, timedelta

def excel_date_to_datetime(val):
    try:
        if isinstance(val, (int, float)) and val > 40000:
            return datetime(1899, 12, 30) + timedelta(days=int(val))
        return pd.to_datetime(val, errors='coerce')
    except:
        return None

xl = pd.ExcelFile('temp_inspect.xlsx')
df = xl.parse(0, header=None)
print(f"Sheet 0 dimensions: {df.shape}")

# Search for key markers
for r in range(min(50, len(df))):
    for c in range(min(20, len(df.columns))):
        val = df.iloc[r, c]
        s_val = str(val).upper().strip()
        
        if 'CIUDAD' in s_val:
            print(f"FOUND 'CIUDAD' at Row {r}, Col {c}")
            
        d_obj = excel_date_to_datetime(val)
        if pd.notna(d_obj):
            d_str = d_obj.strftime('%d-%m-%Y')
            if '2026' in d_str:
                print(f"FOUND DATE {d_str} at Row {r}, Col {c} (Raw: {val})")

# Print a block of data around Row 4
print("\n--- Data around Row 4 ---")
# Replace NaN with dots for cleaner printing
print(df.iloc[0:15, 0:15].fillna('.').to_string())
