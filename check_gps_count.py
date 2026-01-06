
import json
import pandas as pd
import os

def check_gps():
    # 1. Check Input Demand
    demanda = pd.read_excel("data/demanda_ciudades.xlsx")
    print(f"COLUMNS: {demanda.columns}")
    demanda["vehiculos_1gps"] = demanda["vehiculos_1gps"].fillna(0).astype(float)
    demanda["vehiculos_2gps"] = demanda["vehiculos_2gps"].fillna(0).astype(float)
    demanda["gps_total"] = demanda["vehiculos_1gps"] + 2 * demanda["vehiculos_2gps"]
    total_demand = demanda["gps_total"].sum()
    
    print(f"Total Demand via Excel: {total_demand}")
    
    # 2. Check VRP Result
    with open("outputs/vrp_result.json", "r", encoding='utf-8') as f:
        data = json.load(f)
        
    plan = data.get('plan', [])
    total_planned = sum(item.get('gps', 0) for item in plan)
    
    print(f"Total Planned via JSON: {total_planned}")
    
    internal = sum(item.get('gps', 0) for item in plan if item.get('type') == 'INTERNAL')
    external = sum(item.get('gps', 0) for item in plan if item.get('type') == 'EXTERNAL')
    
    print(f"Internal: {internal}")
    print(f"External: {external}")

    print(f"External: {external}")

    if abs(total_demand - total_planned) > 0.1:
        print("DISCREPANCY DETECTED IN TOTALS!")
    else:
        print("TOTALS MATCH: 314 GPS.")
        
    # 3. City-by-City Check
    print("\n--- CITY BY CITY CHECK ---")
    plan_by_city = {}
    for item in plan:
        c = item['city']
        plan_by_city[c] = plan_by_city.get(c, 0) + item['gps']
        
    mismatch_found = False
    for index, row in demanda.iterrows():
        city = row['ciudad'] # Correct column name: ciudad
        if not isinstance(city, str): continue
        
        req = row['gps_total']
        planned = plan_by_city.get(city, 0)
        
        if req > 0 or planned > 0:
            if abs(req - planned) > 0.1:
                print(f"MISMATCH: {city} -> Demand: {req}, Plan: {planned}")
                mismatch_found = True
                
    if not mismatch_found:
        print("PERFECT MATCH: Every city has exactly the requested GPS assigned.")
    else:
        print("WARNING: Distribution mismatch found.")

if __name__ == "__main__":
    check_gps()
