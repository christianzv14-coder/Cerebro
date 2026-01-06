
import json
from collections import defaultdict

def find_gaps():
    with open('outputs/vrp_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Group by (Tech, City)
    # Store list of active days
    assignments = defaultdict(list)

    for entry in data.get('plan', []):
        if entry.get('type') != 'INTERNAL':
            continue
        
        tech = entry.get('tech')
        city = entry.get('city')
        day = entry.get('day')
        
        if tech and city and day:
            assignments[(tech, city)].append(day)

    with open("outputs/gaps.txt", "w") as f:
        f.write(f"{'Tecnico':<15} {'Ciudad':<15} {'Inicio':<6} {'Fin':<6} {'Span':<6} {'Activos':<8} {'Brecha':<6}\n")
        f.write("-" * 70 + "\n")

        for (tech, city), days in assignments.items():
            days = sorted(list(set(days)))
            if not days: continue
            
            start = min(days)
            end = max(days)
            span = end - start + 1
            active = len(days)
            gap = span - active
            
            if gap > 0:
                line = f"{tech:<15} {city:<15} {start:<6} {end:<6} {span:<6} {active:<8} {gap:<6}\n"
                print(line.strip())
                f.write(line)
    print("Gaps written to outputs/gaps.txt")

if __name__ == "__main__":
    find_gaps()
