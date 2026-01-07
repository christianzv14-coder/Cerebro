
import pandas as pd

xl = pd.ExcelFile('temp_inspect.xlsx')
df = xl.parse(1, header=None)
print(f"Sheet 1 dims: {df.shape}")

# Search for CIUDAD
ciudad_found = False
for r in range(len(df)):
    row_vals = [str(x).upper().strip() for x in df.iloc[r].values]
    if 'CIUDAD' in row_vals:
        c_idx = row_vals.index('CIUDAD')
        print(f"FOUND 'CIUDAD' at Row {r}, Col {c_idx}")
        # Print next 5 rows
        print("Data starting here:")
        print(df.iloc[r:r+10].to_string())
        ciudad_found = True
        break

if not ciudad_found:
    print("COULD NOT FIND 'CIUDAD' IN SHEET 1!")
    # Print first few rows of raw data
    print(df.head(10).to_string())
