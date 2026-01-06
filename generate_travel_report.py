
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
    
    # helper
    def load_excel(name, index_col=0):
        p = os.path.join(path, name)
        if os.path.exists(p):
            df = pd.read_excel(p, index_col=index_col)
            # Normalize index/cols
            if index_col == 0:
                df.index = df.index.map(norm_city)
                df.columns = df.columns.map(norm_city)
            return df
        return pd.DataFrame()

    km = load_excel("matriz_distancia_km.xlsx")
    peajes = load_excel("matriz_peajes.xlsx") # UF
    avion_cost = load_excel("matriz_costo_avion.xlsx") # UF
    avion_time = load_excel("matriz_tiempo_avion.xlsx") # Hours
    
    # Params
    params = pd.read_excel(os.path.join(path, "parametros.xlsx"))
    param_dict = dict(zip(params['parametro'], params['valor']))
    
    # Bases
    techs = pd.read_excel(os.path.join(path, "tecnicos_internos.xlsx"))
    techs['tecnico'] = techs['tecnico'].str.strip()
    techs['ciudad_base'] = techs['ciudad_base'].str.strip()
    base_map = dict(zip(techs['tecnico'], techs['ciudad_base']))
    
    # Fletes
    flete = pd.read_excel(os.path.join(path, "flete_ciudad.xlsx"))
    flete['ciudad'] = flete['ciudad'].apply(norm_city)
    flete_map = dict(zip(flete['ciudad'], flete['costo_flete']))
    
    return km, peajes, avion_cost, avion_time, param_dict, base_map, flete_map

def generate_travel_report():
    km, peajes, avion_cost, avion_time, params, base_map, flete_map = load_data()
    
    # Constants
    PRECIO_BENCINA = safe_float(params.get("precio_bencina_uf_km"), 0.0)
    VELOCIDAD = safe_float(params.get("velocidad_terrestre"), 80.0)
    
    # Load Plan
    with open('outputs/vrp_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # --- INTERNAL TRAVELS ---
    tech_events = defaultdict(list)
    active_cities_intenal = set()
    
    for entry in data.get('plan', []):
        if entry.get('type') == 'INTERNAL':
            tech_events[entry.get('tech')].append(entry)
            active_cities_intenal.add(entry.get('city'))
            
    internal_rows = []
    
    def get_trip_cost(origin, dest):
        if origin == dest: return 0.0, 0.0, 0.0, "N/A"
        
        # Land
        dist = safe_float(km.loc[origin, dest], 99999) if (origin in km.index and dest in km.columns) else 99999
        peaje = safe_float(peajes.loc[origin, dest], 0.0) if (origin in peajes.index and dest in peajes.columns) else 0.0
        
        fuel_cost = dist * PRECIO_BENCINA
        total_land = peaje + fuel_cost
        time_land = dist / VELOCIDAD
        
        # Air
        cost_air = safe_float(avion_cost.loc[origin, dest], 99999) if (origin in avion_cost.index and dest in avion_cost.columns) else 99999
        time_air = safe_float(avion_time.loc[origin, dest], 99) if (origin in avion_time.index and dest in avion_time.columns) else 99
        
        # Logic
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

    for tech, events in tech_events.items():
        events.sort(key=lambda x: x['day'])
        
        base = base_map.get(tech, "Santiago")
        current_loc = base
        
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
            
            internal_rows.append({
                "Tecnico": tech,
                "Origen": origin,
                "Destino": dest,
                "Modo": mode,
                "Distancia (km)": dist_val if mode == "Terrestre" else "N/A",
                "Peaje (UF)": peaje_val,
                "Combustible (UF)": fuel_val,
                "Costo Total Viaje (UF)": cost
            })

    # --- FLETES (INTERNAL + EXTERNAL) ---
    fletes_rows = []
    
    # 1. External Cities
    ext_cities = set()
    for entry in data.get('plan', []):
        if entry.get('type') == 'EXTERNAL':
            ext_cities.add(entry.get('city'))
    
    # 2. Internal Remote Bases or Operations
    # Check all active internal cities
    # Rule: If Flete defined (>0) and city used, add cost.
    # We consolidate by City.
    
    all_flete_cities = ext_cities.union(active_cities_intenal)
    
    for city in all_flete_cities:
        cost = flete_map.get(city, 0.0)
        
        if cost > 0:
            # Determine Type
            tipo = "Mixto"
            if city in ext_cities and city not in active_cities_intenal:
                tipo = "Externo"
            elif city in active_cities_intenal and city not in ext_cities:
                if city in base_map.values():
                    tipo = "Interno (Base Remota)"
                else:
                    tipo = "Interno (Operativo)"
            
            fletes_rows.append({
                "Ciudad": city,
                "Tipo": tipo,
                "Concepto": "Envio Materiales",
                "Origen": "Santiago",
                "Costo Flete (UF)": cost
            })

    # Output
    out_path = "outputs/reporte_traslados_v2.xlsx"
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        pd.DataFrame(internal_rows).to_excel(writer, sheet_name="Traslados Detalle", index=False)
        pd.DataFrame(fletes_rows).to_excel(writer, sheet_name="Fletes y Envios", index=False)
        # Note: Params sheet omitted for brevity in v2 unless requested
        
    print(f"Travel report generated: {out_path}")

if __name__ == "__main__":
    generate_travel_report()
