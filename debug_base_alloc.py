
import modelo_optimizacion_gps_chile_v1 as model

# Use model.GPS_TOTAL instead of import from generate_inputs
# Note: model execution on import might be noisy but necessary to inspect state
GPS_TOTAL = model.GPS_TOTAL

print("DEBUG: Checking Base Allocation")
print(f"Forced list: {model.FORCED_EXTERNAL_CITIES}")
print(f"Total Santiago Demand: {GPS_TOTAL.get('Santiago')}")

rem_gps = {c: int(max(0, GPS_TOTAL.get(c, 0))) for c in model.CIUDADES}
rem_gps_internal = rem_gps.copy()
for c in model.FORCED_EXTERNAL_CITIES:
    if c in rem_gps_internal:
        rem_gps_internal[c] = 0

print(f"Santiago available internal: {rem_gps_internal.get('Santiago')}")

for t in model.TECNICOS:
    base = model.base_tecnico(t)
    print(f"Tech {t} Base: '{base}'")
    
    if base == 'Santiago':
        matches = rem_gps_internal.get(base, 0)
        print(f"  Matches demand? {matches}")
        
        gpd = model.gps_por_dia(t)
        dias = model.dias_disponibles_proyecto(t)
        print(f"  Capacity: {gpd} gps/day * {dias} days = {gpd*dias}")
        
        take = min(matches, gpd*dias)
        print(f"  Would take: {take}")
