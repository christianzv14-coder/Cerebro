
import json
import pandas as pd
import os
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
    
    # Helper to load excel matrices
    def load_excel(name, index_col=0):
        p = os.path.join(path, name)
        if os.path.exists(p):
            df = pd.read_excel(p, index_col=index_col)
            # Normalize
            if index_col == 0:
                df.index = df.index.map(norm_city)
                df.columns = df.columns.map(norm_city)
            return df
        return pd.DataFrame()

    km = load_excel("matriz_distancia_km.xlsx")
    peajes = load_excel("matriz_peajes.xlsx")
    avion_cost = load_excel("matriz_costo_avion.xlsx")
    avion_time = load_excel("matriz_tiempo_avion.xlsx")
    
    params = pd.read_excel(os.path.join(path, "parametros.xlsx"))
    param_dict = dict(zip(params['parametro'], params['valor']))
    
    techs = pd.read_excel(os.path.join(path, "tecnicos_internos.xlsx"))
    techs['tecnico'] = techs['tecnico'].str.strip()
    techs['ciudad_base'] = techs['ciudad_base'].str.strip()
    base_map = dict(zip(techs['tecnico'], techs['ciudad_base']))
    
    return km, peajes, avion_cost, avion_time, param_dict, base_map

def generate_daily_report():
    km, peajes, avion_cost, avion_time, params, base_map = load_data()
    
    PRECIO_BENCINA = safe_float(params.get("precio_bencina_uf_km"), 0.0)
    VELOCIDAD = safe_float(params.get("velocidad_terrestre"), 80.0)
    
    with open('outputs/vrp_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    tech_events = defaultdict(list)
    for entry in data.get('plan', []):
        if entry.get('type') == 'INTERNAL':
            tech_events[entry.get('tech')].append(entry)
            
    rows = []
    
    def calculate_cost(origin, dest):
        if origin == dest: return 0.0, 0.0, 0.0, "N/A"
        
        # Land
        dist = safe_float(km.loc[origin, dest], 99999) if (origin in km.index and dest in km.columns) else 99999
        peaje = safe_float(peajes.loc[origin, dest], 0.0) if (origin in peajes.index and dest in peajes.columns) else 0.0
        
        fuel = dist * PRECIO_BENCINA
        total_land = peaje + fuel
        time_land = dist / VELOCIDAD
        
        # Air
        cost_air = safe_float(avion_cost.loc[origin, dest], 99999) if (origin in avion_cost.index and dest in avion_cost.columns) else 99999
        time_air = safe_float(avion_time.loc[origin, dest], 99) if (origin in avion_time.index and dest in avion_time.columns) else 99
        
        # Selection
        mode = "Terrestre"
        final_total = total_land
        final_peaje = peaje
        final_fuel = fuel
        
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
            
        return final_total, final_peaje, final_fuel, mode

    for tech, events in tech_events.items():
        events.sort(key=lambda x: x['day'])
        
        base = base_map.get(tech, "Santiago")
        current_loc = base
        last_day = 0
        
        # 1. First movement logic
        # Usually from base to First City. 
        # When does it happen? Usually Day 1 morning or Day 0?
        # If First Event is Day 1 in City X (and X != Base), travel is Day 1.
        
        for e in events:
            dest_city = e['city']
            day = e['day']
            last_day = max(last_day, day)
            
            if dest_city != current_loc:
                # RECORD TRIP
                cost, peaje, fuel, mode = calculate_cost(current_loc, dest_city)
                
                rows.append({
                    "Tecnico": tech,
                    "Dia": day,
                    "Origen": current_loc,
                    "Destino": dest_city,
                    "Modo": mode,
                    "Peaje (UF)": peaje,
                    "Combustible (UF)": fuel,
                    "Costo Viaje (UF)": cost,
                    "Razon": "Inicio Operativo" if current_loc == base and day == 1 else "Cambio Ciudad"
                })
                current_loc = dest_city
                
        # 2. Return to Base
        if current_loc != base:
            return_day = last_day + 1
            cost, peaje, fuel, mode = calculate_cost(current_loc, base)
            rows.append({
                "Tecnico": tech,
                "Dia": return_day,
                "Origen": current_loc,
                "Destino": base,
                "Modo": mode,
                "Peaje (UF)": peaje,
                "Combustible (UF)": fuel,
                "Costo Viaje (UF)": cost,
                "Razon": "Retorno a Base"
            })

    # Sort
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by=["Dia", "Tecnico"])

    out_path = "outputs/reporte_traslados_diarios.xlsx"
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
        
    print(f"Daily Travel Report generated: {out_path}")

if __name__ == "__main__":
    generate_daily_report()
