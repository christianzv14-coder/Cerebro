
import json

def check_overlaps():
    with open("outputs/vrp_result.json", "r") as f:
        data = json.load(f)
        
    plan = data['plan']
    
    # Check External overlaps
    ext_d0 = 0
    ext_d1 = 0
    
    collision_cities = []
    
    for item in plan:
        if item.get('type') == 'EXTERNAL':
            d = item['day']
            c = item['city']
            g = item['gps']
            
            if d == 0:
                ext_d0 += g
            elif d == 1:
                ext_d1 += g
                
            # Check specific city collision
            # We need to know if SAME city has Day 0 and Day 1
    
    cities_d0 = set(i['city'] for i in plan if i['type'] == 'EXTERNAL' and i['day'] == 0)
    cities_d1 = set(i['city'] for i in plan if i['type'] == 'EXTERNAL' and i['day'] == 1)
    
    collisions = cities_d0.intersection(cities_d1)
    
    print(f"External Day 0 Total: {ext_d0}")
    print(f"External Day 1 Total: {ext_d1}")
    print(f"Colliding Cities (Have both Day 0 and Day 1): {collisions}")
    
    # Specific Check for Antofagasta
    anto_events = [i for i in plan if i['city'] == 'Antofagasta']
    print("\n--- Antofagasta Events ---")
    for e in anto_events:
        print(f"Tech: {e.get('tech')}, Day: {e.get('day')}, GPS: {e.get('gps')}")
        
    # Check Max Day overall
    max_day = max(i['day'] for i in plan)
    print(f"\nMax Day in Plan: {max_day}")
    
    if collisions:
        print("CRITICAL: Data is being overwritten if Day 0 is mapped to Day 1 without summing.")

if __name__ == "__main__":
    check_overlaps()
