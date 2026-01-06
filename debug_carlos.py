
import json

def debug_carlos():
    with open('outputs/vrp_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Filter Carlos
    events = [e for e in data['plan'] if e.get('tech') == 'Carlos' and e.get('type') == 'INTERNAL']
    
    # Sort by Day
    events.sort(key=lambda x: x['day'])
    
    print(f"{'Dia':<5} {'Ciudad':<15}")
    print("-" * 25)
    for e in events:
        print(f"{e['day']:<5} {e['city']:<15}")

if __name__ == "__main__":
    debug_carlos()
