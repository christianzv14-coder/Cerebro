
import json

try:
    with open("outputs/pure_routing_result.json", "r") as f:
        data = json.load(f)
        
    print(f"Pure Routing Total Cost: {data['cost_total']:.2f} UF")
    
except Exception as e:
    print(f"Error: {e}")
