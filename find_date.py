
import pandas as pd
xl = pd.ExcelFile('temp_inspect.xlsx')
df = xl.parse(0, header=None)
print(f"Sheet 0 dimensions: {df.shape}")
for r in range(len(df)):
    for c in range(len(df.columns)):
        v = str(df.iloc[r, c])
        if '19-01-2026' in v:
            print(f"Found at R{r} C{c}: {v}")
