
import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt

# 1. DATA INPUTS
# ==========================================
# CITIES & DEMAND (Lat/Lon approximated for Chile)
cities_data = {
    'Santiago': {'gps': 19, 'lat': -33.4489, 'lon': -70.6693},
    'Temuco': {'gps': 14, 'lat': -38.7359, 'lon': -72.5904},
    'Antofagasta': {'gps': 13, 'lat': -23.6509, 'lon': -70.3975},
    'Chillan': {'gps': 12, 'lat': -36.6063, 'lon': -72.1023},
    'Talca': {'gps': 9, 'lat': -35.4264, 'lon': -71.6554},
    'Coquimbo': {'gps': 8, 'lat': -29.9533, 'lon': -71.3436},
    'Puerto Montt': {'gps': 6, 'lat': -41.4689, 'lon': -72.9411},
    'La Serena': {'gps': 6, 'lat': -29.9027, 'lon': -71.2519},
    'Concepción': {'gps': 6, 'lat': -36.8270, 'lon': -73.0503},
    'Chiloé': {'gps': 5, 'lat': -42.6174, 'lon': -73.9273}, # Using Castro as proxy
    'Curicó': {'gps': 5, 'lat': -34.9854, 'lon': -71.2394},
    'Rancagua': {'gps': 5, 'lat': -34.1701, 'lon': -70.7444},
    'Valparaíso': {'gps': 5, 'lat': -33.0472, 'lon': -71.6127},
    'Los Ángeles': {'gps': 4, 'lat': -37.4697, 'lon': -72.3537},
    'Curanilahue': {'gps': 4, 'lat': -37.4764, 'lon': -73.3442},
    'Calama': {'gps': 0, 'lat': -22.4542, 'lon': -68.9292} # Base only
}

# RESOURCES (Technicians)
# User Request: Optimization with ONLY 3 TECHNICIANS (FINAL DECISION)
technicians = [
    {'name': 'Luis', 'base': 'Santiago'},
    # {'name': 'Wilmer', 'base': 'Santiago'},
    # {'name': 'Fabian D.', 'base': 'Santiago'},
    # {'name': 'Efrain', 'base': 'Santiago'},
    {'name': 'Jimmy', 'base': 'Chillan'},
    # {'name': 'Carlos', 'base': 'Santiago'},
    {'name': 'Orlando', 'base': 'Calama'}
]

# PARAMETERS
# With fewer techs, duration might increase, but cost might stay similar (just less parallel)
COST_PER_KM = 300 # CLP
# Breakdown of Daily Expenses (Total was 40k)
ALMUERZO_DIA = 18000
MOVILIZACION_DIA = 5000
VIATICO_GRAL_DIA = 17000 # Cena + Otros
# Total check: 18+5+17 = 40k (Consistent with previous approved budget)

ALOJAMIENTO_NOCHE = 60000 # CLP
INSTALL_TIME_HOURS = 1.15
WORK_HOURS_DAY = 8
MAX_DAYS_PROJECT = 15

# 2. HELPER FUNCTIONS
# ==========================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371 # Earth radius in km
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def calculate_days_needed(gps_count):
    # Total hours needed
    total_hours = gps_count * INSTALL_TIME_HOURS
    # Days needed (rounding up for logistics)
    return max(1, np.ceil(total_hours / WORK_HOURS_DAY))

# 3. ASSIGNMENT LOGIC (HARDCODED PER USER REQUEST)
# ==========================================
# User explicitly stated: "LUIS NO HACE LA SERENA", "JIMMY NO HACE TALCA"
# This implies a strict zonal division overriding simple distance.

MANUAL_ASSIGNMENTS = {
    'Orlando': ['Antofagasta', 'Calama', 'Coquimbo', 'La Serena'],
    'Luis': ['Curicó', 'Rancagua', 'Santiago', 'Talca', 'Valparaíso'],
    'Jimmy': ['Chillan', 'Chiloé', 'Concepción', 'Curanilahue', 'Los Ángeles', 'Puerto Montt', 'Temuco']
}

base_clusters = {t['base']: [] for t in technicians}
tech_base_map = {t['name']: t['base'] for t in technicians}

print("--- APPLYING MANUAL ASSIGNMENTS ---")
for tech_name, assigned_cities in MANUAL_ASSIGNMENTS.items():
    base = tech_base_map.get(tech_name)
    if not base: continue # Skip if tech not active
    
    for city in assigned_cities:
        if city not in cities_data: continue
        gps_count = cities_data[city]['gps']
        if gps_count == 0 and city != base: continue # Skip empty cities except base
        
        # Calculate dist just for sorting later
        clat, clon = cities_data[city]['lat'], cities_data[city]['lon']
        blat, blon = cities_data[base]['lat'], cities_data[base]['lon']
        dist = haversine(clat, clon, blat, blon)
        
        base_clusters[base].append({'city': city, 'dist': dist, 'gps': gps_count})
        print(f"Assigning {city} to {tech_name} ({base}) - Manual Override")

# 4. ROUTE GENERATION & COSTING
# ==========================================
print("\n--- GENERATING LOGISTICS PLAN ---")
total_project_cost = 0
plan_details = []
granular_details = [] # Initialize here (Global for later use)

for base, tasks in base_clusters.items():
    # Filter techs at this base
    base_techs = [t['name'] for t in technicians if t['base'] == base]
    if not base_techs: continue
    
    # Sort tasks by distance (Route optimization heuristic: Nearest Neighbor)
    # OLD: tasks.sort(key=lambda x: x['dist']) 
    
    # NEW: Chain Optimization (TSP Greedy)
    # 1. Distribute tasks to techs FIRST (Load Balancing)
    # Simple strategy: Assign to tech with strictly fewest items? Or round robin?
    # Let's keep Round Robin for simplicity as load is roughly balanced by zones.
    tech_queues = {t: [] for t in base_techs}
    for i, task in enumerate(tasks): # Note: tasks is currently sorted by dist-from-base. 
        # Better: Sort by dist-from-base to assign closer things first? 
        # Or just assign randomly? Round robin on "closest to base" is decent for partitioning.
        tasks.sort(key=lambda x: x['dist'])
        tech_idx = i % len(base_techs)
        tech_queues[base_techs[tech_idx]].append(task)
        
    # 2. Optimize Each Tech's Queue (Sort the chain)
    for tech, queue in tech_queues.items():
        if not queue: continue
        
        # Optimize Queue Order: Nearest Neighbor Chain
        optimized_queue = []
        unvisited = queue.copy()
        current_lat, current_lon = cities_data[base]['lat'], cities_data[base]['lon']
        
        while unvisited:
            best_next = None
            min_dist_leg = float('inf')
            best_idx = -1
            
            for idx, cand in enumerate(unvisited):
                # Dist from current
                c_lat, c_lon = cities_data[cand['city']]['lat'], cities_data[cand['city']]['lon']
                d = haversine(current_lat, current_lon, c_lat, c_lon)
                if d < min_dist_leg:
                    min_dist_leg = d
                    best_next = cand
                    best_idx = idx
            
            # Commit Move
            optimized_queue.append(best_next)
            current_lat = cities_data[best_next['city']]['lat']
            current_lon = cities_data[best_next['city']]['lon']
            unvisited.pop(best_idx)
            
        # Execute the Optimized Chain
        current_loc = base
        total_km = 0
        total_almuerzo = 0
        total_movilizacion = 0
        total_viatico_gral = 0
        total_lodging = 0
        
        route_str = [base]
        
        # Start Row for Granular
        granular_details.append({
            'Técnico': tech, 'Origen': 'BASE', 'Destino': base, 'Km': 0, 'Bencina': 0, 
            'Almuerzo': 0, 'Movilidad': 0, 'Viatico': 0, 'Hotel': 0, 'Total': 0,
            'GPS': 0, 'Días': 0
        })

        for stop in optimized_queue:
            city_name = stop['city']
            gps_count = stop['gps']
            
            # Travel Base/Prev -> City
            d = haversine(cities_data[current_loc]['lat'], cities_data[current_loc]['lon'],
                          cities_data[city_name]['lat'], cities_data[city_name]['lon'])
            total_km += d
            
            # Work at City
            days = calculate_days_needed(gps_count)
            
            # Daily Costs
            total_almuerzo += days * ALMUERZO_DIA
            total_movilizacion += days * MOVILIZACION_DIA
            total_viatico_gral += days * VIATICO_GRAL_DIA
            
            # Lodging
            if city_name == base:
                lodging_cost = 0 
            else:
                lodging_cost = ALOJAMIENTO_NOCHE * days
                
            total_lodging += lodging_cost
            
            # Granular Row
            c_alm = days * ALMUERZO_DIA
            c_mov = days * MOVILIZACION_DIA
            c_via = days * VIATICO_GRAL_DIA
            c_hot = lodging_cost
            c_ben = d * COST_PER_KM
            
            granular_details.append({
                'Técnico': tech,
                'Origen': current_loc,
                'Destino': city_name,
                'Km': int(d),
                'Bencina': int(c_ben),
                'Almuerzo': int(c_alm),
                'Movilidad': int(c_mov),
                'Viatico': int(c_via),
                'Hotel': int(c_hot),
                'Total': int(c_ben + c_alm + c_mov + c_via + c_hot),
                'GPS': gps_count,
                'Días': int(days)
            })

            current_loc = city_name
            route_str.append(f"{city_name}({int(days)}d)")
            
        # Return to Base
        d_return = haversine(cities_data[current_loc]['lat'], cities_data[current_loc]['lon'],
                             cities_data[base]['lat'], cities_data[base]['lon'])
        total_km += d_return
        route_str.append(base)
        
        # Return Trip Row
        granular_details.append({
            'Técnico': tech,
            'Origen': current_loc,
            'Destino': base + " (Retorno)",
            'Km': int(d_return),
            'Bencina': int(d_return * COST_PER_KM),
            'Almuerzo': 0, 'Movilidad': 0, 'Viatico': 0, 'Hotel': 0,
            'Total': int(d_return * COST_PER_KM),
            'GPS': 0, 'Días': 0
        })
        
        travel_cost = total_km * COST_PER_KM
        tech_total = travel_cost + total_almuerzo + total_movilizacion + total_viatico_gral + total_lodging
        
        total_project_cost += tech_total
        
        plan_details.append({
            'Tech': tech,
            'Base': base,
            'Route': " -> ".join(route_str),
            'Km': int(total_km),
            'Travel ($)': int(travel_cost),
            'Almuerzo ($)': int(total_almuerzo),
            'Movilidad ($)': int(total_movilizacion),
            'Viatico Gral ($)': int(total_viatico_gral),
            'Lodging ($)': int(total_lodging),
            'Total ($)': int(tech_total)
        })

df_granular = pd.DataFrame(granular_details)
df_granular.to_excel("outputs/detalle_rutas_granular_desglosado.xlsx", index=False)
print("Granular detailed report saved to outputs/detalle_rutas_granular_desglosado.xlsx")

# NEW: Generate JSON for Legacy Gantt (generate_gantt_final.py)
import json

json_data = {'plan': []}

# Iterate per Tech to build timeline
# granular_details list already has the sequence
# We need to assign specific calendar days (1..15)

tech_timelines = {} 

for item in granular_details:
    tech = item['Técnico']
    city = item['Destino']
    days = item['Días']
    gps = item['GPS']
    
    if tech not in tech_timelines:
        tech_timelines[tech] = 1 # Start Day 1
        
    start_day = tech_timelines[tech]
    
    # If it's a visit (days > 0)
    if days > 0:
        # Fix: Handle integer division remainders to ensure accurate Sum (121)
        base_gps = int(gps // days)
        remainder = int(gps % days)
        
        for d in range(days):
            current_gantt_day = start_day + d
            
            val_for_day = base_gps
            if d < remainder:
                val_for_day += 1
            
            json_entry = {
                'city': city,
                'tech': tech,
                'gps': val_for_day, 
                'day': int(current_gantt_day),
                'type': 'INTERNAL'
            }
            json_data['plan'].append(json_entry)
            
        tech_timelines[tech] += days # Advance timeline
        
    elif "Retorno" in city:
        # Just advance one day for travel
        tech_timelines[tech] += 1

with open("outputs/vrp_result.json", "w") as f:
    json.dump(json_data, f, indent=4)
    
print("JSON for Gantt saved to outputs/vrp_result.json")
