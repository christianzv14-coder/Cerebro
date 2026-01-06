import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt

# 1. PARAMETERS
# ========================
WORK_HOURS_DAY = 9
COST_PER_KM = 300
ALOJAMIENTO_NOCHE = 60000
ALMUERZO_DIA = 18000
MOVILIZACION_DIA = 5000
VIATICO_GRAL_DIA = 17000

# 2. DATA
# ========================
# 1GPS = 0.5 hours, 2GPS = 1.0 hours
raw_data = [
    {'city': 'Antofagasta', 'v1': 0, 'v2': 11, 'lat': -23.6509, 'lon': -70.3975},
    {'city': 'Arica', 'v1': 0, 'v2': 6, 'lat': -18.4783, 'lon': -70.3126},
    {'city': 'Calama', 'v1': 0, 'v2': 2, 'lat': -22.4542, 'lon': -68.9292},
    {'city': 'Caldera', 'v1': 0, 'v2': 11, 'lat': -27.0685, 'lon': -70.8192},
    {'city': 'Castro', 'v1': 0, 'v2': 2, 'lat': -42.6174, 'lon': -73.9273},
    {'city': 'Chillán', 'v1': 2, 'v2': 0, 'lat': -36.6063, 'lon': -72.1023},
    {'city': 'Concepción', 'v1': 5, 'v2': 2, 'lat': -36.8270, 'lon': -73.0503},
    {'city': 'Copiapó', 'v1': 2, 'v2': 0, 'lat': -27.3668, 'lon': -70.3323},
    {'city': 'Coquimbo', 'v1': 8, 'v2': 3, 'lat': -29.9533, 'lon': -71.3436},
    {'city': 'Coronel', 'v1': 0, 'v2': 1, 'lat': -37.0167, 'lon': -73.1333},
    {'city': 'Iquique', 'v1': 2, 'v2': 31, 'lat': -20.2307, 'lon': -70.1357},
    {'city': 'Lautaro', 'v1': 3, 'v2': 16, 'lat': -38.5333, 'lon': -72.4500},
    {'city': 'Linares', 'v1': 4, 'v2': 1, 'lat': -35.8454, 'lon': -71.5979},
    {'city': 'Los Ángeles', 'v1': 3, 'v2': 0, 'lat': -37.4697, 'lon': -72.3537},
    {'city': 'Mejillones', 'v1': 5, 'v2': 49, 'lat': -23.1000, 'lon': -70.4500},
    {'city': 'Osorno', 'v1': 3, 'v2': 0, 'lat': -40.5739, 'lon': -73.1335},
    {'city': 'Ovalle', 'v1': 1, 'v2': 0, 'lat': -30.5983, 'lon': -71.2003},
    {'city': 'Pichirropulli', 'v1': 1, 'v2': 0, 'lat': -40.0333, 'lon': -72.9333},
    {'city': 'Puerto Aysen', 'v1': 2, 'v2': 4, 'lat': -45.4000, 'lon': -72.7000},
    {'city': 'Puerto Montt', 'v1': 3, 'v2': 29, 'lat': -41.4689, 'lon': -72.9411},
    {'city': 'Puerto Natales', 'v1': 3, 'v2': 0, 'lat': -51.7267, 'lon': -72.5067},
    {'city': 'Puerto Williams', 'v1': 1, 'v2': 0, 'lat': -54.9333, 'lon': -67.6167},
    {'city': 'Punta Arenas', 'v1': 4, 'v2': 12, 'lat': -53.1638, 'lon': -70.9171},
    {'city': 'Romeral', 'v1': 1, 'v2': 0, 'lat': -34.9667, 'lon': -71.1333},
    {'city': 'San Antonio', 'v1': 2, 'v2': 1, 'lat': -33.5833, 'lon': -71.6167},
    {'city': 'San Fernando', 'v1': 1, 'v2': 17, 'lat': -34.5833, 'lon': -70.9833},
    {'city': 'San Vicente', 'v1': 5, 'v2': 33, 'lat': -34.4333, 'lon': -71.0667},
    {'city': 'Santiago', 'v1': 11, 'v2': 90, 'lat': -33.4489, 'lon': -70.6693},
    {'city': 'Talca', 'v1': 0, 'v2': 1, 'lat': -35.4264, 'lon': -71.6554},
    {'city': 'Valdivia', 'v1': 0, 'v2': 1, 'lat': -39.8142, 'lon': -73.2459},
    {'city': 'Valparaiso', 'v1': 10, 'v2': 58, 'lat': -33.0472, 'lon': -71.6127},
]

technicians = [
    {'name': 'Orlando', 'base': 'Calama'},
    {'name': 'Pedro (Norte)', 'base': 'Calama'},
    {'name': 'Luis', 'base': 'Santiago'},
    {'name': 'Wilmer', 'base': 'Santiago'},
    {'name': 'Jimmy', 'base': 'Chillán'},
    {'name': 'Carlos (Sur)', 'base': 'Santiago'}
]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

# 3. PROCESSING
# ========================
cities_data = {}
for r in raw_data:
    # Hours: v1*0.5 + v2*1.0
    hours = (r['v1'] * 0.5) + (r['v2'] * 1.0)
    days = max(1, np.ceil(hours / WORK_HOURS_DAY))
    
    cities_data[r['city']] = {
        'lat': r['lat'],
        'lon': r['lon'],
        'v1': r['v1'],
        'v2': r['v2'],
        'hours': hours,
        'days': int(days)
    }

# 4. ASSIGNMENT (Hybrid: Internal vs External)
# ========================
EXTERNAL_THRESHOLD_KM = 400 # Max radius for internal techs
base_clusters = {t['base']: [] for t in technicians}
external_tasks = []

unassigned = [c for c in cities_data.keys()]

print("--- CLUSTERING (AUTO-EXTERNALIZATION) ---")
for city in unassigned:
    best_base = None
    min_dist = float('inf')
    clat, clon = cities_data[city]['lat'], cities_data[city]['lon']
    
    # 1.5. Manual Overrides (Fix Orlando & North)
    # Force "Norte Chico" and "Calama" to Orlando/Calama Base
    # This prevents them from being Externalized due to >400km or bugs.
    force_calama_cluster = ['Calama', 'Coquimbo', 'Ovalle', 'Copiapó', 'Caldera', 'Vallenar', 'La Serena']
    
    if city in force_calama_cluster:
        base_clusters['Calama'].append({'city': city, 'dist': 0}) # Dist 0 to force prio/group
        print(f"{city} -> Calama (FORCED INTERNAL)")
        continue

    # 1. Find closest internal base
    for base in base_clusters.keys():
        if base not in cities_data: continue
        blat, blon = cities_data[base]['lat'], cities_data[base]['lon']
        d = haversine(clat, clon, blat, blon)
        if d < min_dist:
            min_dist = d
            best_base = base
            
    # 2. Decision: Internal or External?
    if min_dist > EXTERNAL_THRESHOLD_KM:
        # Too far -> External
        print(f"{city} -> EXTERNAL (Region Far: {int(min_dist)} km > {EXTERNAL_THRESHOLD_KM})")
        external_tasks.append({'city': city, 'gps': cities_data[city]['v1']+cities_data[city]['v2']})
    else:
        # Keep Internal
        base_clusters[best_base].append({'city': city, 'dist': min_dist})
        print(f"{city} -> {best_base} ({int(min_dist)} km)")

# ... Processing Internals ...


# 5. ROUTING & REPORT
# ========================
plan_rows = []
total_cost = 0

for base, tasks in base_clusters.items():
    base_techs = [t['name'] for t in technicians if t['base'] == base]
    if not base_techs: continue
    
    # Sort tasks by distance
    tasks.sort(key=lambda x: x['dist'])
    
    # Distribute Round Robin
    tech_queues = {t: [] for t in base_techs}
    for i, task in enumerate(tasks):
        tech_idx = i % len(base_techs)
        tech_queues[base_techs[tech_idx]].append(task)
        
    # Process Queues
    for tech, queue in tech_queues.items():
        if not queue: continue
        
        # Optimize Chain (Nearest Neighbor)
        optimized_q = []
        unvisited = queue.copy()
        curr_lat, curr_lon = cities_data[base]['lat'], cities_data[base]['lon']
        
        while unvisited:
            best_idx = -1
            min_d = float('inf')
            for i, item in enumerate(unvisited):
                c_name = item['city']
                c_lat, c_lon = cities_data[c_name]['lat'], cities_data[c_name]['lon']
                d = haversine(curr_lat, curr_lon, c_lat, c_lon)
                if d < min_d:
                    min_d = d
                    best_idx = i
            
            # Commit
            nxt = unvisited.pop(best_idx)
            optimized_q.append(nxt)
            curr_lat = cities_data[nxt['city']]['lat']
            curr_lon = cities_data[nxt['city']]['lon']

        # Calculate Sequence Cost
        current_loc = base
        
        for stop in optimized_q:
            city = stop['city']
            stats = cities_data[city]
            days = stats['days']
            
            # Distance
            d = haversine(cities_data[current_loc]['lat'], cities_data[current_loc]['lon'],
                          cities_data[city]['lat'], cities_data[city]['lon'])
            
            # Costs Breakdown
            c_bencina = int(d * COST_PER_KM)
            c_almuerzo = int(days * ALMUERZO_DIA)
            c_movilidad = int(days * MOVILIZACION_DIA)
            c_viatico = int(days * VIATICO_GRAL_DIA)
            c_hotel = 0 if city == base else int(days * ALOJAMIENTO_NOCHE)
            
            # Incentive Calculation: 8 points * $570 * Total_GPS
            total_gps_city = stats['v1'] + stats['v2']
            c_incentivo = int(total_gps_city * 8 * 570)
            
            total_step = c_bencina + c_almuerzo + c_movilidad + c_viatico + c_hotel + c_incentivo
            total_cost += total_step
            
            # Debug Valpo
            if 'Valparaiso' in city or 'Valparaíso' in city:
                print(f"[DEBUG] {city}: V1={stats['v1']}, V2={stats['v2']}, Hours={stats['hours']}, Days={days}")
            
            plan_rows.append({
                'Técnico': tech,
                'Origen': current_loc,
                'Destino': city,
                'V1': stats['v1'],
                'V2': stats['v2'],
                'GPS_Total': total_gps_city,
                'Horas': stats['hours'],
                'Días': int(days),
                'Km': int(d),
                'Bencina': c_bencina,
                'Almuerzo': c_almuerzo,
                'Movilidad': c_movilidad,
                'Viatico Gral': c_viatico,
                'Hotel': c_hotel,
                'Incentivo': c_incentivo,
                'Total': total_step
            })
            current_loc = city
            
        # Return
        d_ret = haversine(cities_data[current_loc]['lat'], cities_data[current_loc]['lon'],
                          cities_data[base]['lat'], cities_data[base]['lon'])
        c_ret_bne = int(d_ret * COST_PER_KM)
        total_cost += c_ret_bne
        plan_rows.append({
                'Técnico': tech,
                'Origen': current_loc,
                'Destino': 'BASE',
                'V1': 0, 'V2': 0, 'GPS_Total': 0, 'Horas': 0, 'Días': 0,
                'Km': int(d_ret),
                'Bencina': c_ret_bne,
                'Almuerzo': 0, 'Movilidad': 0, 'Viatico Gral': 0, 'Hotel': 0, 'Incentivo': 0,
                'Total': c_ret_bne
        })

# Process External Tasks
for item in external_tasks:
    city = item['city']
    stats = cities_data[city]
    
    # Cost Model for External: Flat rate or Just 0 Logistics?
    # User asked to "optimize cost", implying removing the logistics overhead.
    # But Incentives (pay per GPS) likely apply as the "Service Cost".
    # 8 points * 570 * GPS
    
    total_gps = stats['v1'] + stats['v2']
    c_incentivo = int(total_gps * 8 * 570)
    
    plan_rows.append({
        'Técnico': 'EXTERNAL',
        'Origen': '-',
        'Destino': city,
        'V1': stats['v1'], 'V2': stats['v2'], 'GPS_Total': total_gps, 
        'Horas': stats['hours'], 'Días': stats['days'],
        'Km': 0, 'Bencina': 0, 'Almuerzo': 0, 'Movilidad': 0, 'Viatico Gral': 0, 'Hotel': 0,
        'Incentivo': c_incentivo,
        'Total': c_incentivo # External Cost is just the incentive/service fee
    })

df_out = pd.DataFrame(plan_rows)
print(f"Total Cost (Internal Logistics): ${int(total_cost):,}")

# Generate simple summary for console
print("\n--- RESUMEN POR TÉCNICO ---")
summary = df_out.groupby('Técnico')[['Total', 'Km', 'Días']].sum()
print(summary.to_string())

df_out.to_excel("outputs/plan_enex_detalle_granular.xlsx", index=False)

# NEW: JSON Export for Gantt
import json

json_data = {'plan': []}
tech_timelines = {} 

# We need to reconstruct the timeline from plan_rows
# plan_rows contains the sequence per tech already
for row in plan_rows:
    tech = row['Técnico']
    city = row['Destino']
    days = row['Días']
    v1 = row['V1']
    v2 = row['V2']
    total_gps = v1 + v2 # Just for count
    
    if tech not in tech_timelines:
        tech_timelines[tech] = 1
        
    start_day = tech_timelines[tech]
    
    if days > 0 and city != 'BASE':
        # Distribute GPS across days
        # Simple distribution: 1 per day? No, we have counts.
        # Let's just put average.
        
        gps_per_day = int(total_gps // days)
        remainder = int(total_gps % days)
        
        for d in range(days):
            current_day = start_day + d
            val = gps_per_day
            if d < remainder:
                val += 1
                
            json_data['plan'].append({
                'city': city,
                'tech': tech,
                'gps': val,
                'day': int(current_day),
                'type': 'INTERNAL'
            })
            
        tech_timelines[tech] += days
        
    elif city == 'BASE' or "(Ret)" in city:
        # Travel back day? Row has Días=0 usually for return distinct row?
        # In my code: Return row has Días=0.
        # Let's add 1 day for travel return visualization
        tech_timelines[tech] += 1

with open("outputs/vrp_result_enex.json", "w") as f:
    json.dump(json_data, f, indent=4)
print("JSON for Gantt saved to outputs/vrp_result_enex.json")
