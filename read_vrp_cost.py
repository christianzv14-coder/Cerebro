
import json

try:
    with open("outputs/vrp_result.json", "r") as f:
        data = json.load(f)
        
    print(f"Op Cost: {data['cost_operational']:.2f} UF")
    print(f"Total Cost: {data['cost_total']:.2f} UF")
    
except Exception as e:
    print(f"Error: {e}")
