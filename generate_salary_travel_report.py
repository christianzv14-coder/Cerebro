
import json
import pandas as pd
import os
import math
from collections import defaultdict

def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default

def norm_city(x):
    return str(x).strip()

def load_data():
    path = "data"
    
    # Load Tech Data
    techs = pd.read_excel(os.path.join(path, "tecnicos_internos.xlsx"))
    techs['tecnico'] = techs['tecnico'].str.strip()
    tech_info = techs.set_index('tecnico').to_dict('index')
    
    # Load Params
    params = pd.read_excel(os.path.join(path, "parametros.xlsx"))
    param_dict = dict(zip(params['parametro'], params['valor']))
    
    return tech_info, param_dict

def generate_report():
    tech_info, params = load_data()
    
    # Constants for Salary Calculation
    HH_MES = safe_float(params.get("hh_mes"), 180.0)
    DIAS_SEMANA = safe_float(params.get("dias_semana"), 6)
    SEMANAS_PROY = safe_float(params.get("semanas_proyecto"), 4)
    H_DIA = safe_float(params.get("horas_jornada"), 9.0) # Check default in code? default 7 in code.
    # Actually shared.py says default 7.0
    H_DIA = safe_float(params.get("horas_jornada"), 7.0) 

    # Load Result to get Days
    with open('outputs/vrp_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # --- 1. SALARY DETAIL ---
    salary_rows = []
    
    # Reconstruct timeline to count Total Days in Project per Technician
    # Wait, the formula is: `sueldo_mes * (hh_project / hh_mes)`.
    # This is the "Total Project Cost" for that tech.
    # Then it is distributed.
    # The user probably wants to see "How much I pay the tech for this project".
    
    tech_stats = defaultdict(lambda: {'days': 0, 'cities': set()})
    
    # Calculate Active Days from Plan
    for entry in data.get('plan', []):
        if entry.get('type') == 'INTERNAL':
            t = entry.get('tech')
            tech_stats[t]['days'] += 1
            tech_stats[t]['cities'].add(entry.get('city'))
            
    # Iterate all technicians in input (even if not used?) No, only assigned.
    for tech_name, props in tech_info.items():
        if tech_name not in tech_stats:
            continue # Skip if not used
            
        sueldo_mes = safe_float(props.get('sueldo_uf'), 0.0)
        hh_semana = safe_float(props.get('hh_semana_proyecto'), 0.0)
        
        # Calculation Steps
        hh_proyecto = hh_semana * SEMANAS_PROY
        factor_prorrateo = hh_proyecto / HH_MES
        costo_proyecto_total = sueldo_mes * factor_prorrateo
        
        # Operational Days (from JSON)
        active_days = tech_stats[tech_name]['days']
        
        salary_rows.append({
            "Tecnico": tech_name,
            "Sueldo Mes (UF)": sueldo_mes,
            "HH Semanales": hh_semana,
            "Semanas Proy": SEMANAS_PROY,
            "HH Totales Proy": hh_proyecto,
            "HH Mes Base": HH_MES,
            "Factor Prorrateo": factor_prorrateo,
            "Costo Total Asignado (UF)": costo_proyecto_total,
            "Dias Activos (Plan)": active_days,
            "Formula": "(SueldoMes / HH_Mes) * HH_Proy"
        })
        
    df_salary = pd.DataFrame(salary_rows)
    
    # --- 2. TRAVEL DETAIL (Re-calculated) ---
    # Load Matrices
    def load_excel(name, index_col=0):
        p = os.path.join("data", name)
        if os.path.exists(p):
            df = pd.read_excel(p, index_col=index_col)
            if index_col == 0:
                df.index = df.index.map(norm_city)
                df.columns = df.columns.map(norm_city)
            return df
        return pd.DataFrame()

    km = load_excel("matriz_distancia_km.xlsx")
    peajes = load_excel("matriz_peajes.xlsx")
    avion_cost = load_excel("matriz_costo_avion.xlsx")
    avion_time = load_excel("matriz_tiempo_avion.xlsx")
    
    PRECIO_BENCINA = safe_float(params.get("precio_bencina_uf_km"), 0.0)
    VELOCIDAD = safe_float(params.get("velocidad_terrestre"), 80.0)
    
    # Base Map
    # techs dataframe is not in scope, use tech_info
    base_map = {tech: info.get('ciudad_base', 'Santiago') for tech, info in tech_info.items()}
    
    # Internal Events
    tech_events_travel = defaultdict(list)
    for entry in data.get('plan', []):
        if entry.get('type') == 'INTERNAL':
            tech_events_travel[entry.get('tech')].append(entry)

    travel_rows = []
    
    def get_trip_cost(origin, dest):
        if origin == dest: return 0.0, 0.0, 0.0, "N/A", "N/A"
        
        dist = safe_float(km.loc[origin, dest], 99999) if (origin in km.index and dest in km.columns) else 99999
        peaje = safe_float(peajes.loc[origin, dest], 0.0) if (origin in peajes.index and dest in peajes.columns) else 0.0
        
        fuel_cost = dist * PRECIO_BENCINA
        total_land = peaje + fuel_cost
        time_land = dist / VELOCIDAD
        
        cost_air = safe_float(avion_cost.loc[origin, dest], 99999) if (origin in avion_cost.index and dest in avion_cost.columns) else 99999
        time_air = safe_float(avion_time.loc[origin, dest], 99) if (origin in avion_time.index and dest in avion_time.columns) else 99
        
        mode = "Terrestre"
        final_total = total_land
        final_peaje = peaje
        final_fuel = fuel_cost
        
        if time_land > 5.6 and time_air <= 5.6:
            mode = "Avion"
            final_total = cost_air
            final_peaje = 0
            final_fuel = 0
        elif cost_air < total_land:
            mode = "Avion"
            final_total = cost_air
            final_peaje = 0
            final_fuel = 0
            
        return final_total, final_peaje, final_fuel, dist if mode=="Terrestre" else 0, mode

    for tech, events in tech_events_travel.items():
        events.sort(key=lambda x: x['day'])
        base = base_map.get(tech, "Santiago")
        
        # Trace path
        visited_cities = []
        last_c = None
        for e in events:
            c = e['city']
            if c != last_c:
                visited_cities.append(c)
                last_c = c
        itinerary = [base] + visited_cities + [base]
        
        clean_itinerary = [itinerary[0]]
        for c in itinerary[1:]:
            if c != clean_itinerary[-1]:
                clean_itinerary.append(c)
                
        for i in range(len(clean_itinerary) - 1):
            origin = clean_itinerary[i]
            dest = clean_itinerary[i+1]
            cost, peaje_val, fuel_val, dist_val, mode = get_trip_cost(origin, dest)
            
            travel_rows.append({
                "Tecnico": tech,
                "Origen": origin,
                "Destino": dest,
                "Modo": mode,
                "Distancia (km)": dist_val,
                "Peaje (UF)": peaje_val,
                "Combustible (UF)": fuel_val,
                "Costo Total Viaje (UF)": cost
            })
            
    df_travel = pd.DataFrame(travel_rows)

    # --- 3. OUTPUT ---
    out_path = "outputs/reporte_sueldos_traslados_completo.xlsx"
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        df_salary.to_excel(writer, sheet_name="Detalle Sueldos", index=False)
        df_travel.to_excel(writer, sheet_name="Detalle Traslados", index=False)
    print(f"Report generated: {out_path}")

if __name__ == "__main__":
    generate_report()
