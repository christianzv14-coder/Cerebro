
import pandas as pd
import numpy as np
from collections import defaultdict
import math
from ortools.sat.python import cp_model

# Import shared data and parameters
import json
import os

# Import shared data and parameters
import modelo_optimizacion_gps_chile_v1 as shared

print("=== INITIATING VRP MODEL (OR-TOOLS) ===")

def solve_vrp():
    model = cp_model.CpModel()

    # --- DATA PREP ---
    TECNICOS = shared.TECNICOS
    CIUDADES = shared.CIUDADES
    DIAS = list(range(1, shared.DIAS_MAX + 1)) # 1..24
    
    # Mappings for Indexing
    t_idx = {t: i for i, t in enumerate(TECNICOS)}
    c_idx = {c: i for i, c in enumerate(CIUDADES)}
    idx_t = {i: t for t, i in t_idx.items()}
    idx_c = {i: c for c, i in c_idx.items()}
    
    num_techs = len(TECNICOS)
    num_cities = len(CIUDADES)
    num_days = len(DIAS)
    
    # Demands
    demand = {c: int(max(0, shared.GPS_TOTAL.get(c, 0))) for c in CIUDADES}
    
    # Forced Externals
    forced_cities = ["Arica", "Punta Arenas", "Coyhaique"]
    
    # --- VARIABLES ---
    
    # x[t, d, c] = 1 if Tech t is in City c on Day d
    x = {} 
    for t in range(num_techs):
        for d in range(num_days):
            for c in range(num_cities):
                x[t, d, c] = model.NewBoolVar(f'x_{t}_{d}_{c}')
                
    # work[t, d, c] = Amount of GPS installed by T in C on Day D (0..3)
    work = {}
    for t in range(num_techs):
        for d in range(num_days):
            for c in range(num_cities):
                work[t, d, c] = model.NewIntVar(0, 3, f'work_{t}_{d}_{c}')

    # external[c] = Amount of GPS externalized in C
    external = {}
    for c in range(num_cities):
        max_dem = demand[idx_c[c]]
        external[c] = model.NewIntVar(0, max_dem, f'ext_{c}')

    # --- CONSTRAINTS ---


    # 0. DISTANCE CONSTRAINT (600 KM Limit)
    # 600 km * 0.00342 UF/km = 2.052 UF
    MAX_VIAJE_UF = 2.052
    
    for t in range(num_techs):
        base_t = shared.base_tecnico(idx_t[t])
        
        for c in range(num_cities):
            c_name = idx_c[c]
            
            # Check cost from Base to City
            # (Assuming Terrestrial move is the limiting factor for "Range")
            cost_from_base = shared.costo_viaje_uf(base_t, c_name, "terrestre")
            
            if cost_from_base > MAX_VIAJE_UF:
                 # Technicians CANNOT be in this city.
                 # Block assignment for all days
                 for d in range(num_days):
                     model.Add(x[t, d, c] == 0)

    # 1. Spatial Uniqueness: A tech is in exactly one city per day
    for t in range(num_techs):
        for d in range(num_days):
            model.Add(sum(x[t, d, c] for c in range(num_cities)) == 1)

    # 2. Work Consistency
    for t in range(num_techs):
        real_tech = idx_t[t]
        gpd = int(shared.gps_por_dia(real_tech))
        
        for d in range(num_days):
            day_num = DIAS[d]
            
            # Sunday Logic: No work on Sundays (Days 7, 14, 21...)
            # Day 1 is Monday? In previous logic check: if day % 7 == 0 (Sunday).
            # shared.DIAS_MAX is 24.
            is_sunday = (day_num % 7 == 0)
            
            for c in range(num_cities):
                # Work can only happen if Tech is present
                model.Add(work[t, d, c] <= gpd * x[t, d, c])
                
                # If Sunday, Work = 0
                if is_sunday:
                    model.Add(work[t, d, c] == 0)

    # 3. Demand Satisfaction
    for c in range(num_cities):
        total_internal = sum(work[t, d, c] for t in range(num_techs) for d in range(num_days))
        model.Add(total_internal + external[c] == demand[idx_c[c]])

    # 4. Forced External Logic
    for c_name in forced_cities:
        if c_name in c_idx:
            c_i = c_idx[c_name]
            # Internal work must be 0
            model.Add(sum(work[t, d, c_i] for t in range(num_techs) for d in range(num_days)) == 0)

    # 5. Base Start Constraint (Day 1)
    # Techs start at their base (or allow them to travel immediately Day 1?)
    # Usually they wake up at Base. Move happens during the day.
    # Logic in previous script: sleep_city = base. Manana: Travel or Work.
    # Here: x[t, 0, c] implies "Where do they sleep at END of Day 1?"
    # Let's say x[t, -1, base] = 1.
    pass 

    # --- OBJECTIVE FUNCTION (PURE ROUTING) ---
    obj_terms = []
    SCALE = 100

    # 1. PRIORITY: MAXIMIZE INTERNAL WORK (Minimize External)
    # Huge penalty for every GPS externalized
    PENALTY_EXTERNAL = 100000
    for c in range(num_cities):
        obj_terms.append(external[c] * int(PENALTY_EXTERNAL * SCALE))
        
    # 2. SECONDARY: MINIMIZE TRAVEL DISTANCE/FRICTION
    # We use 'dist_uf' as a proxy for Distance/Time friction.
    
    # Transitions
    for t in range(num_techs):
        base_t = shared.base_tecnico(idx_t[t])
        
        # Day 0
        for c_to in range(num_cities):
             dist_uf_land = shared.costo_viaje_uf(base_t, idx_c[c_to], "terrestre")
             dist_uf_air = shared.costo_viaje_uf(base_t, idx_c[c_to], "avion")
             if dist_uf_air < 0.1: dist_uf_air = 999999.0
             dist_uf = min(dist_uf_land, dist_uf_air)
             
             cost_val = int(dist_uf * SCALE) # Only Distance Friction
             
             if cost_val > 0:
                 obj_terms.append(x[t, 0, c_to] * cost_val)

        # Day d -> d+1
        for d in range(num_days - 1):
            for c_from in range(num_cities):
                for c_to in range(num_cities):
                    c_from_name = idx_c[c_from]
                    c_to_name = idx_c[c_to]
                    
                    dist_uf_land = shared.costo_viaje_uf(c_from_name, c_to_name, "terrestre")
                    dist_uf_air = shared.costo_viaje_uf(c_from_name, c_to_name, "avion")
                    if c_from_name != c_to_name and dist_uf_air < 0.1: dist_uf_air = 999999.0
                    dist_uf = min(dist_uf_land, dist_uf_air)
                    
                    # Hotel/Lunch ignored in routing decision
                    friction_cost = int(dist_uf * SCALE)
                    
                    if friction_cost > 0:
                        trans = model.NewBoolVar(f'tr_{t}_{d}_{c_from}_{c_to}')
                        model.AddBoolOr([x[t, d, c_from].Not(), x[t, d+1, c_to].Not(), trans])
                        obj_terms.append(trans * friction_cost)

    # --- SOLVE ---
    model.Minimize(sum(obj_terms))
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    status = solver.Solve(model)
    
    print(f"Status: {solver.StatusName(status)}")
    
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("Solution found (Pure Routing Objective). Calculating Real Financial Cost...")
        
        # --- CALCULATE REAL COST (Not Objective) ---
        real_op_cost = 0.0
        
        # 1. Salaries (Fixed)
        real_op_cost += sum(shared.costo_sueldo_proyecto_uf(t) for t in TECNICOS)
        
        # 2. Lunch (Fixed 24 days)
        real_op_cost += num_techs * num_days * shared.ALMU_UF
        
        # 3. Incentives
        total_work_gps = sum(solver.Value(work[t, d, c]) for t in range(num_techs) for d in range(num_days) for c in range(num_cities))
        real_op_cost += total_work_gps * shared.INCENTIVO_UF
        
        # 4. External Costs (Real)
        for c in range(num_cities):
             qty = solver.Value(external[c])
             if qty > 0:
                 vals = shared.costo_externo_uf(idx_c[c], qty)
                 real_op_cost += vals["total_externo_sin_materiales_uf"]
        
        # 5. Transitions (Real)
        for t in range(num_techs):
            base_t = shared.base_tecnico(idx_t[t])
            # Day 0
            for c_to in range(num_cities):
                if solver.Value(x[t, 0, c_to]):
                     c_to_name = idx_c[c_to]
                     dist_uf_land = shared.costo_viaje_uf(base_t, c_to_name, "terrestre")
                     dist_uf_air = shared.costo_viaje_uf(base_t, c_to_name, "avion")
                     if dist_uf_air < 0.1: dist_uf_air = 999999.0
                     real_cost_trip = min(dist_uf_land, dist_uf_air)
                     
                     hotel_cost = shared.ALOJ_UF if c_to_name != base_t else 0.0
                     real_op_cost += (real_cost_trip + hotel_cost)

            # Day d->d+1
            for d in range(num_days - 1):
                # Find From/To from solution to avoid N^2 check?
                # Helper: find pos
                # But iterating x[t,d,c] is fast enough (7 techs * 24 days).
                c_from_idx = -1
                for c in range(num_cities):
                    if solver.Value(x[t, d, c]):
                        c_from_idx = c
                        break
                
                c_to_idx = -1
                for c in range(num_cities):
                    if solver.Value(x[t, d+1, c]):
                        c_to_idx = c
                        break
                        
                if c_from_idx != -1 and c_to_idx != -1:
                     c_from_name = idx_c[c_from_idx]
                     c_to_name = idx_c[c_to_idx]
                     
                     dist_uf_land = shared.costo_viaje_uf(c_from_name, c_to_name, "terrestre")
                     dist_uf_air = shared.costo_viaje_uf(c_from_name, c_to_name, "avion")
                     if dist_uf_air < 0.1: dist_uf_air = 999999.0
                     real_cost_trip = min(dist_uf_land, dist_uf_air)
                     
                     hotel_cost = shared.ALOJ_UF if c_to_name != base_t else 0.0
                     real_op_cost += (real_cost_trip + hotel_cost)

        obj_val_uf = real_op_cost # Overwrite for JSON
        
        print(f"Total Cost (Real Financial - Op Only): {obj_val_uf:.2f} UF")
        
        # Calculate Material Cost manually
        mat_cost = sum(shared.costo_materiales_ciudad(c) for c in CIUDADES)
        total_project_cost = obj_val_uf + mat_cost
        print(f"Total Project Cost (Real Financial): {total_project_cost:.2f} UF")

        # Extract Plan
        plan_data = []
        print("\n--- PLAN SUMMARY ---")
        for t in range(num_techs):
            t_name = idx_t[t]
            print(f"Tech {t_name}:")
            for d in range(num_days):
                for c in range(num_cities):
                    if solver.Value(x[t, d, c]):
                        w_val = solver.Value(work[t, d, c])
                        c_name = idx_c[c]
                        if w_val > 0 or c_name != shared.base_tecnico(t_name):
                            print(f"  Day {d+1}: {c_name} (Inst: {w_val})")
                            plan_data.append({
                                "tech": t_name, "day": d+1, "city": c_name, "gps": w_val, "type": "INTERNAL"
                            })
        
        # External Plan
        for c in range(num_cities):
            ext_qty = solver.Value(external[c])
            if ext_qty > 0:
                c_name = idx_c[c]
                print(f"External {c_name}: {ext_qty} GPS")
                plan_data.append({
                    "tech": "External", "day": 0, "city": c_name, "gps": ext_qty, "type": "EXTERNAL"
                })

        # Save to JSON
        output = {
            "cost_operational": obj_val_uf,
            "cost_materials": mat_cost,
            "cost_total": total_project_cost,
            "plan": plan_data
        }
        with open("outputs/pure_routing_result.json", "w") as f:
            json.dump(output, f, indent=4)
            
    else:
        print("No solution found.")

if __name__ == "__main__":
    solve_vrp()
