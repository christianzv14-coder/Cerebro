
import pandas as pd
import os

path = "data/"
files = ["parametros.xlsx", "demanda_ciudades.xlsx", "tecnicos_internos.xlsx", "materiales.xlsx"]

for f in files:
    fp = os.path.join(path, f)
    if os.path.exists(fp):
        try:
            df = pd.read_excel(fp)
            print(f"\n--- {f} ---")
            print("Columns:", df.columns.tolist())
            print("First row:", df.iloc[0].values if not df.empty else "Empty")
        except:
            print(f"Error reading {f}")
