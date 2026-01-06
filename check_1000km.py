
import pandas as pd
import modelo_optimizacion_gps_chile_v1 as shared

bases = ["Santiago", "Chillan", "Calama"]
print(f"=== REACHABLE CITIES (< 1000 KM) ===")

reached = {b: [] for b in bases}


# 1000 km * 0.00342 UF/km = 3.42 UF
MAX_COST_VIAJE = 3.42

for b in bases:
    print(f"\nBase: {b}")
    for c in shared.CIUDADES:
        cost = shared.costo_viaje_uf(b, c, "terrestre")
        # Approximate distance
        dist_approx = cost / 0.00342 if cost > 0 else 0
        
        if cost <= MAX_COST_VIAJE:
            print(f"  ✅ {c}: ~{dist_approx:.0f} km")
            reached[b].append(c)
        else:
            print(f"  ❌ {c}: ~{dist_approx:.0f} km (BLOCKED)")

print("\nSummary of Coverage:")
for b, cities in reached.items():
    print(f"{b}: {len(cities)} cities")
