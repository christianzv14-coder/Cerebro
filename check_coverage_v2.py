
import pandas as pd
import os

path = "data/matriz_distancia_km.xlsx"
df = pd.read_excel(path, index_col=0)
existing = set([str(x).strip() for x in df.index])

required = [
    "Santiago", "Rancagua", "San Antonio", "San Fernando", "Viña del Mar", "Talca",
    "San Felipe", "Copiapo", "Antofagasta", "La Serena", "Calama", "Iquique", "Arica",
    "Temuco", "Concepcion", "Chillan", "Puerto Montt", "Osorno", "Los Angeles",
    "Punta Arenas", "Coyhaique"
]

missing = [c for c in required if c not in existing]

print("--- MISSING CITIES ---")
for m in missing:
    print(m)
print("----------------------")
