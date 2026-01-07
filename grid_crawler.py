
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

all_demand = []
# 1. Map all date cells
date_cells = [] # (r, c, d_str)
for r in range(len(df)):
    for c in range(len(df.columns)):
        val = df.iloc[r, c]
        d_obj = excel_date_to_datetime(val)
        if pd.notna(d_obj):
            d_str = d_obj.strftime('%d-%m-%Y')
            if '2026' in d_str:
                date_cells.append((r, c, d_str))

print(f"Total date cells found: {len(date_cells)}")

# 2. For each date cell, find the city and value
# Assuming the City is to the left (same row) or nearby
for rd, cd, d_str in date_cells:
    # Scan rows below this date cell until we hit another date or end
    for r in range(rd + 1, len(df)):
        # If we hit another date in this column, stop
        if any(rd_new == r and cd_new == cd for rd_new, cd_new, _ in date_cells):
            break
        
        val = df.iloc[r, cd]
        try:
            q_val = float(val)
            if q_val > 0:
                # Find City Name in Col 3 (as usual) or nearby
                city = "UNKNOWN"
                # Search left in the same row
                for c_search in range(cd - 1, -1, -1):
                    c_val = str(df.iloc[r, c_search]).strip()
                    if c_val != 'nan' and c_val != '' and not c_val.replace('.','').isdigit():
                        city = c_val.upper()
                        break
                all_demand.append({'City': city, 'Day': d_str, 'Qty': int(q_val)})
        except:
            pass

print(f"Total demand items found: {len(all_demand)}")
# Count by day
df_res = pd.DataFrame(all_demand)
if not df_res.empty:
    print(df_res['Day'].value_counts().sort_index())
