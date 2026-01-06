
import pandas as pd
import os

# New cities required
new_cities = [
    "Santiago", "Rancagua", "San Antonio", "San Fernando", "Viña del Mar", "Talca",
    "San Felipe", "Copiapo", "Antofagasta", "La Serena", "Calama", "Iquique", "Arica",
    "Temuco", "Concepcion", "Chillan", "Puerto Montt", "Osorno", "Los Angeles",
    "Punta Arenas", "Coyhaique"
]

# Normalize function from model
def norm_city(x):
    if pd.isna(x): return x
    return str(x).strip()

path = "data/"
matrices = ["matriz_distancia_km.xlsx", "matriz_peajes.xlsx", "matriz_costo_avion.xlsx", "matriz_tiempo_avion.xlsx"]

print("Checking city coverage...")
missing_total = set()

for m in matrices:
    fp = os.path.join(path, m)
    if os.path.exists(fp):
        df = pd.read_excel(fp, index_col=0)
        df.index = df.index.map(norm_city)
        df.columns = df.columns.map(norm_city)
        
        # Check rows and cols
        current_cities = set(df.index)
        missing = [c for c in new_cities if c not in current_cities]
        
        if missing:
            print(f"\n[MISSING] In {m}: {missing}")
            missing_total.update(missing)
        else:
            print(f"[OK] {m} covers all cities.")

if not missing_total:
    print("\nAll matrices are ready!")
else:
    print(f"\nTotal missing cities to add: {list(missing_total)}")
