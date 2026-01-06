
import pandas as pd
import numpy as np
import os
import math
from collections import defaultdict

# --- USER DEFINED SCENARIO ---
SCENARIO_EXTERNOS = {
    "Santiago": 37,
    "Talca": 9,
    "Copiapo": 8,
    "Antofagasta": 10,
    "La Serena": 13,
    "Calama": 4,
    "Iquique": 4,
    "Arica": 4,
    "Temuco": 15,
    "Puerto Montt": 7,
    "Osorno": 8,
    "Punta Arenas": 3,
    "Coyhaique": 1
}

SCENARIO_INTERNOS = {
    "Rancagua": 10,
    "Santiago": 98,
    "San Antonio": 5,
    "San Fernando": 16,
    "Viña del Mar": 26,
    "San Felipe": 5,
    "Concepcion": 16,
    "Chillan": 7,
    "Los Angeles": 8
}

import modelo_optimizacion_gps_chile_v1 as model

def run_scenario():
    print("=== EVALUANDO CONTRA-EJEMPLO USUARIO ===")
    
    cost_ext_total = 0.0
    flete_ext_total = 0.0
    rows_ext = []
    
    print("\n--- EXTERNOS (Calculo Directo) ---")
    for city, qty in SCENARIO_EXTERNOS.items():
        city_norm = model.norm_city(city)
        pxq_unit = model.safe_float(model.PXQ_UF_POR_GPS.get(city_norm, 0.0), 0.0)
        pxq = qty * pxq_unit
        
        fle = 0.0
        if model.flete_aplica(city_norm, "Santiago", "terrestre"):
             fle = model.safe_float(model.FLETE_UF.get(city_norm, 0.0), 0.0)
        
        if city_norm == "Santiago":
            fle = 0.0
            
        total_city = pxq + fle
        cost_ext_total += pxq
        flete_ext_total += fle
        
        rows_ext.append({
            "Ciudad": city, "Qty": qty, "PXQ_Unit": pxq_unit,
            "PXQ_Total": pxq, "Flete": fle, "Total": total_city
        })
        print(f"  {city}: {qty} GPS -> {total_city:.2f} UF (PXQ: {pxq:.2f}, Flete: {fle:.2f})")
        
    print(f"TOTAL EXTERNOS: {cost_ext_total + flete_ext_total:.2f} UF (Servicios: {cost_ext_total:.2f}, Flete: {flete_ext_total:.2f})")

    print("\n--- INTERNOS (Simulacion Logica) ---")
    
    model.GPS_TOTAL = {model.norm_city(k): v for k, v in SCENARIO_INTERNOS.items()}
    for c in model.CIUDADES:
        if c not in model.GPS_TOTAL:
            model.GPS_TOTAL[c] = 0
            
    try:
        rem_gps = {c: int(max(0, model.GPS_TOTAL.get(c, 0))) for c in model.CIUDADES}
        gps_asignados = {t: defaultdict(int) for t in model.TECNICOS}
        tech_state = {}
        for t in model.TECNICOS:
            tech_state[t] = {
                'current_city': model.base_tecnico(t),
                'days_used': 0.0,
                'active': True
            }
            base = model.base_tecnico(t)
            if rem_gps.get(base, 0) > 0:
                 gpd = model.gps_por_dia(t)
                 dias_cap = model.dias_disponibles_proyecto(t)
                 max_gps = dias_cap * gpd
                 take = min(rem_gps[base], max_gps)
                 gps_asignados[t][base] += take
                 rem_gps[base] -= take
                 days_task = take / max(1, gpd)
                 tech_state[t]['days_used'] += days_task

        while True:
            cities_with_demand = [c for c, q in rem_gps.items() if q > 0]
            if not cities_with_demand: break
            active_techs = [t for t in model.TECNICOS if tech_state[t]['active']]
            if not active_techs: break
            active_techs.sort(key=lambda t: tech_state[t]['days_used'])
            current_tech = active_techs[0]
            curr_loc = tech_state[current_tech]['current_city']
            
            reachable = []
            for c in cities_with_demand:
                if c == curr_loc: 
                    tv=0
                else:
                    md = model.choose_mode(curr_loc, c)
                    tv = model.t_viaje(curr_loc, c, md)
                
                if tv <= 5.6:
                    reachable.append((c, tv))
            
            if not reachable:
                tech_state[current_tech]['active'] = False
                continue
                
            reachable.sort(key=lambda x: x[1])
            best_city, tv = reachable[0]
            
            qty_needed = rem_gps[best_city]
            gpd = model.gps_por_dia(current_tech)
            dias_cap = model.dias_disponibles_proyecto(current_tech)
            current_load = tech_state[current_tech]['days_used']
            travel_cost_days = tv / model.horas_diarias(current_tech) if model.horas_diarias(current_tech)>0 else 1
            days_left = dias_cap - current_load - travel_cost_days
            
            max_qty = max(0, int(days_left * gpd))
            
            take = min(qty_needed, max_qty)
            if take <= 0:
                tech_state[current_tech]['active'] = False
                continue
            
            gps_asignados[current_tech][best_city] += take
            rem_gps[best_city] -= take
            tech_state[current_tech]['days_used'] += (take/max(1,gpd)) + travel_cost_days
            tech_state[current_tech]['current_city'] = best_city

        total_internal_uf = 0.0
        internal_details = {}
        for t in model.TECNICOS:
             cities = [c for c, g in gps_asignados[t].items() if g > 0]
             base = model.base_tecnico(t)
             if base in cities:
                 cities = [base] + [c for c in cities if c != base]
             
             plan, cst, pending = model.simulate_tech_schedule(t, cities, gps_asignados[t])
             
             total_internal_uf += cst["total_uf"]
             internal_details[t] = cst
             
             print(f"  {t}: {cst['total_uf']:.2f} UF (Sueldo: {cst['sueldo_uf']:.2f}, Logistica: {cst['travel_uf']+cst['aloj_uf']+cst['alm_uf']:.2f}, Flete: {cst['flete_uf']:.2f})")
             
        # --- AGGREGATE TOTALS FOR REPORT ---
        # 1. Materials
        total_gps_cnt = sum(SCENARIO_EXTERNOS.values()) + sum(SCENARIO_INTERNOS.values())
        mat_cost = 0.0
        for c, q in SCENARIO_EXTERNOS.items():
            mat_cost += model.costo_materiales_ciudad(model.norm_city(c))
        for c, q in SCENARIO_INTERNOS.items():
            mat_cost += model.costo_materiales_ciudad(model.norm_city(c))
        
        # 2. Terceros
        total_terceros_pxq = cost_ext_total
        
        # 3. Alojamientos
        total_aloj = sum(d["aloj_uf"] for d in internal_details.values())
        
        # 4. Traslados Regiones
        total_travel_region = sum(d["travel_uf"] for d in internal_details.values())
        
        # 5. Traslados Internos
        total_internal_transport = sum(d.get("traslado_interno_uf", 0.0) for d in internal_details.values())
        
        # 6. Almuerzos
        total_lunch = sum(d["alm_uf"] for d in internal_details.values())
        
        # 7. Tecnico Base
        total_salary = sum(d["sueldo_uf"] for d in internal_details.values())
        
        # 8. Incentivos
        total_incentives = sum(d["inc_uf"] for d in internal_details.values())
        
        # 9. Flete Scl Chile
        total_flete_internal = sum(d["flete_uf"] for d in internal_details.values())
        total_flete = flete_ext_total + total_flete_internal

        print("\n--- DESGLOSE FINAL SOLICITADO ---")
        print(f"Costo Compra Accesorios: {mat_cost:.2f} UF")
        print(f"Terceros (Servicios Externos): {total_terceros_pxq:.2f} UF")
        print(f"Alojamientos: {total_aloj:.2f} UF")
        print(f"Traslados Regiones: {total_travel_region:.2f} UF")
        print(f"Traslados internos: {total_internal_transport:.2f} UF")
        print(f"Almuerzos: {total_lunch:.2f} UF")
        print(f"Tecnico Base: {total_salary:.2f} UF")
        print(f"Tecnicos Puntos (Incentivos): {total_incentives:.2f} UF")
        print(f"Flete Scl Chile: {total_flete:.2f} UF")
        
        grand_total = mat_cost + total_terceros_pxq + total_aloj + total_travel_region + total_internal_transport + total_lunch + total_salary + total_incentives + total_flete
        print(f"TOTAL SUMA: {grand_total:.2f} UF")
        
    except Exception as e:
        print(f"Error running logic: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_scenario()
