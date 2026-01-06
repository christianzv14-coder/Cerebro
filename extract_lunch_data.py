
import json
import pandas as pd
from collections import defaultdict

def extract_data():
    with open('outputs/vrp_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    city_stats = defaultdict(lambda: {
        'techs': set(), 
        'man_days': 0, 
        'duration_days': set()
    })

    # Parse Plan
    for entry in data.get('plan', []):
        c = entry.get('city')
        if not c: continue
        
        t_type = entry.get('type')
        tech_name = entry.get('tech')
        day = entry.get('day')
        
        if t_type == 'INTERNAL':
            city_stats[c]['techs'].add(tech_name)
            city_stats[c]['man_days'] += 1
            city_stats[c]['duration_days'].add(day)
        else:
            # External
            city_stats[c]['techs'].add("Externo")
            # Externals usually don't have time duration in this model (day=0)
            
    # Output to Excel
    rows = []
    sorted_cities = sorted(city_stats.keys())
    
    for c in sorted_cities:
        stats = city_stats[c]
        
        # Filter "Externo" from count
        real_techs = [t for t in stats['techs'] if t != "Externo"]
        n_techs = len(real_techs)
        
        if stats['duration_days']:
            duration = len(stats['duration_days'])
        else:
            duration = 0
        
        names = ", ".join(sorted(list(stats['techs'])))
        
        rows.append({
            "Ciudad": c,
            "N° Tecnicos": n_techs,
            "Dias (Duracion)": duration,
            "Nombres": names
        })
        
    df = pd.DataFrame(rows)
    out_path = "outputs/datos_almuerzo.xlsx"
    df.to_excel(out_path, index=False)
    print(f"\nData written to {out_path}")

if __name__ == "__main__":
    extract_data()
