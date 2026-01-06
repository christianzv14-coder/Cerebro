
import json
import pandas as pd

def analyze_luis():
    # 1. Get Luis's Base
    techs = pd.read_excel("data/tecnicos_internos.xlsx")
    # Clean column names just in case
    techs.columns = [c.strip().lower() for c in techs.columns]
    print(f"COLUMNS: {techs.columns}")
    
    # Try to find 'Luis' or similar in 'tecnico' or 'nombre'
    col_name = 'tecnico' if 'tecnico' in techs.columns else 'nombre'
    
    luis_row = techs[techs[col_name].astype(str).str.contains("Luis", case=False, na=False)]
    
    if not luis_row.empty:
        base = luis_row.iloc[0]['ciudad_base'] # Correct column name
        print(f"Technician: Luis")
        print(f"Base: {base}")
    else:
        print("Luis not found in technicians file.")
        base = "Santiago" # Default assumption
        
    # 2. Get Luis's Plan
    with open("outputs/vrp_result.json", "r") as f:
        data = json.load(f)
        
    plan = [i for i in data['plan'] if 'Luis' in i.get('tech', '')]
    plan.sort(key=lambda x: x['day'])
    
    print("\n--- LUIS ITINERARY ---")
    current_loc = base
    total_gps = 0
    total_dist = 0 # Approximate if we load matrix, but let's look at flow first
    
    # Load Distances for context
    dist_matrix = pd.read_excel("data/matriz_distancia_km.xlsx", index_col=0)
    
    for item in plan:
        dest = item['city']
        day = item['day']
        gps = item['gps']
        
        dist = 0
        if current_loc in dist_matrix.index and dest in dist_matrix.columns:
            dist = dist_matrix.loc[current_loc, dest]
            
        print(f"Day {day}: Moves {current_loc} -> {dest} ({dist} km). Installs {gps} GPS.")
        
        current_loc = dest
        total_gps += gps
        
    print(f"\nTotal Installations: {total_gps}")

if __name__ == "__main__":
    analyze_luis()
