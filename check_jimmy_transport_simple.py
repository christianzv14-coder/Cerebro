
import pandas as pd
import json

def check_jimmy_transport_simple():
    # Hardcoded Params to avoid lock
    speed = 80.0
    max_drive_hours = 5.6
    
    print(f"Params: Speed={speed} km/h, Max Land Time={max_drive_hours} h")
    
    # 2. Get Sequence
    tech_name = "Jimmy"
    base = "Chillan"
    
    with open("outputs/vrp_result.json", "r") as f:
        data = json.load(f)
    plan = [i for i in data['plan'] if tech_name in i.get('tech', '')]
    plan.sort(key=lambda x: x['day'])
    
    sequence = [base]
    for item in plan:
        city = item['city']
        if city != sequence[-1]:
            sequence.append(city)
            
    # Add return to base
    if sequence[-1] != base:
        sequence.append(base)
        
    print(f"\nSequence: {sequence}")
    
    # 3. Check Each Leg
    dist_matrix = pd.read_excel("data/matriz_distancia_km.xlsx", index_col=0)
    
    print("\n--- TRAVEL MODE CHECK ---")
    all_land = True
    
    for i in range(len(sequence)-1):
        origin = sequence[i]
        dest = sequence[i+1]
        
        dist = 0
        if origin in dist_matrix.index and dest in dist_matrix.columns:
            dist = dist_matrix.loc[origin, dest]
            
        hours = dist / speed
        mode = "TERRESTRE"
        if hours > max_drive_hours:
            mode = "AEREO (POSIBLE)" 
            
        print(f"{origin} -> {dest}: {dist} km, {hours:.2f} hrs. Mode: {mode}")
        
        if mode != "TERRESTRE":
            all_land = False
            
    if all_land:
        print("\nCONCLUSION: YES, ALL TRIPS ARE TERRESTRIAL.")
    else:
        print("\nCONCLUSION: Some trips might be Air.")

if __name__ == "__main__":
    check_jimmy_transport_simple()
