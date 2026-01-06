
import json
import pandas as pd

def analyze_jimmy():
    # 1. Base Info
    tech_name = "Jimmy"
    base = "Chillan" # Confirmed in previous step
    
    print(f"Technician: {tech_name}")
    print(f"Base: {base}")
    
    # 2. Get Plan
    with open("outputs/vrp_result.json", "r") as f:
        data = json.load(f)
        
    plan = [i for i in data['plan'] if tech_name in i.get('tech', '')]
    plan.sort(key=lambda x: x['day'])
    
    # Print Condensed Sequence
    sequence = [base]
    for item in plan:
        city = item['city']
        if city != sequence[-1]:
            sequence.append(city)
            
    print(f"SEQUENCE: {' -> '.join(sequence)}")
    
    # Also print start/end dates for context
    print(f"Start: {plan[0]['day']}, End: {plan[-1]['day']}")

if __name__ == "__main__":
    analyze_jimmy()
