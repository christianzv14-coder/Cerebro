
import modelo_optimizacion_gps_chile_v1 as model
from collections import defaultdict

# Override Forced Externals to match current state
model.FORCED_EXTERNAL_CITIES = ["Arica", "Punta Arenas", "Coyhaique"]

def debug_alloc():
    print("DEBUG ALLOC START")
    tech_cities = {} # unused
    
    # Copy logic from allocation function to instrument it
    rem_gps = {c: int(max(0, model.GPS_TOTAL.get(c, 0))) for c in model.CIUDADES}
    rem_gps_internal = rem_gps.copy()
    for c in model.FORCED_EXTERNAL_CITIES:
        if c in rem_gps_internal:
            rem_gps_internal[c] = 0
            
    gps_asignados = {t: defaultdict(int) for t in model.TECNICOS}
    tech_state = {}
    for t in model.TECNICOS:
        tech_state[t] = { 'current_city': model.base_tecnico(t), 'days_used': 0.0, 'active': True }
        # Anchor logic (simplified)
        base = model.base_tecnico(t)
        if rem_gps_internal.get(base, 0) > 0:
             gpd = model.gps_por_dia(t)
             dias_cap = model.dias_disponibles_proyecto(t)
             max_gps = dias_cap * gpd
             take = min(rem_gps_internal[base], max_gps)
             gps_asignados[t][base] += take
             rem_gps_internal[base] -= take
             tech_state[t]['days_used'] += take / max(1, gpd)
             print(f"ANCHOR: {t} took {take} at {base}")

    steps = 0
    while True:
        steps += 1
        if sum(rem_gps_internal.values()) <= 0:
            print("Done: No more internal demand.")
            break
            
        cities_with_demand = [c for c, q in rem_gps_internal.items() if q > 0]
        if not cities_with_demand: break
        
        active_techs = [t for t in model.TECNICOS if tech_state[t]['active']]
        if not active_techs:
            print("Done: No active techs.")
            break
            
        active_techs.sort(key=lambda t: tech_state[t]['days_used'])
        current_tech = active_techs[0]
        curr_loc = tech_state[current_tech]['current_city']
        
        # Heuristic Connectivity Check
        reachable = []
        for c in cities_with_demand:
            if c == curr_loc: 
                tv = 0.0
                reachable.append((c, tv))
            else:
                tv_road = model.t_viaje(curr_loc, c, "terrestre")
                tv_air = model.t_viaje(curr_loc, c, "avion")
                modes = []
                if tv_road <= 5.6: modes.append(("terrestre", tv_road))
                if tv_air <= 5.6: modes.append(("avion", tv_air))
                
                if modes:
                    # Pick best (min tv)
                    modes.sort(key=lambda x: x[1])
                    reachable.append((c, modes[0][1]))

        if not reachable:
            print(f"Tech {current_tech} at {curr_loc} STRANDED. Demand left: {len(cities_with_demand)} cities.")
            # Print unchecked demand to see what's unreachable
            print(f"Unreachable examples: {cities_with_demand[:3]}")
            tech_state[current_tech]['active'] = False
            continue
            
        reachable.sort(key=lambda x: x[1])
        best_city, tv = reachable[0]
        
        qty_needed = rem_gps_internal[best_city]
        gpd = model.gps_por_dia(current_tech)
        dias_cap = model.dias_disponibles_proyecto(current_tech)
        current_load = tech_state[current_tech]['days_used']
        travel_cost_days = tv / model.horas_diarias(current_tech) if model.horas_diarias(current_tech)>0 else 1.0
        days_left = dias_cap - current_load - travel_cost_days
        
        max_qty = max(0, int(days_left * gpd))
        take = min(qty_needed, max_qty)
        
        if take <= 0:
            print(f"Tech {current_tech} FULL/DONE. DaysUsed: {current_load:.2f}, Cap: {dias_cap:.2f}")
            tech_state[current_tech]['active'] = False
            # Check if he could have taken 0 but traveled?
            # Current logic requires take > 0 to move.
            continue
            
        gps_asignados[current_tech][best_city] += take
        rem_gps_internal[best_city] -= take
        tech_state[current_tech]['days_used'] += (take / max(1, gpd)) + travel_cost_days
        tech_state[current_tech]['current_city'] = best_city
        print(f"Step {steps}: {current_tech} -> {best_city} ({take} gps). New Loc: {best_city}")

if __name__ == "__main__":
    debug_alloc()
