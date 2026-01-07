
import pandas as pd
import os

files = ["data/demanda_ciudades.xlsx", "data/parametros.xlsx", "data/tecnicos_internos.xlsx"]

for f in files:
    if os.path.exists(f):
        print(f"\n--- {f} ---")
        df = pd.read_excel(f)
        print("Columns:", df.columns.tolist())
        print(df.head(20))
    else:
        print(f"{f} not found.")
