import pandas as pd
import modelo_optimizacion_gps_chile_v1 as shared

cities_to_check = [
    "Chillan", "Talca", "Copiapo", "Antofagasta", "La Serena", 
    "Calama", "Iquique", "Arica", "Temuco", "Puerto Montt", 
    "Osorno", "Punta Arenas", "Coyhaique"
]


print("DEBUG keys in shared:", dir(shared))
# Ensure FLETE_UF is there
if not hasattr(shared, 'FLETE_UF'):
    print("CRITICAL: FLETE_UF missing from shared module.")
    # Fallback or Exit
    
with open("outputs/flete_table.txt", "w", encoding="utf-8") as f:
    f.write(f"{'Ciudad':<15} {'Flete (UF)':<10}\n")
    f.write("-" * 30 + "\n")
    
    for c in cities_to_check:
        # fuzzy match or direct get
        if hasattr(shared, 'FLETE_UF'):
             val = shared.FLETE_UF.get(c, 0.0)
        else:
             val = -1.0

        # Try normalizing if 0
        if val == 0:
            # Try finding key with similar name
            for k in shared.FLETE_UF.keys():
                if c.lower() in k.lower():
                   val = shared.FLETE_UF[k]
                   c = k # Use found name
                   break
        
        f.write(f"{c:<15} {val:<10.3f}\n")

print("Flete table written to outputs/flete_table.txt")
