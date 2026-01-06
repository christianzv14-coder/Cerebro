import json
import pandas as pd
import os
from collections import defaultdict

def generate_report():
    # 1. Load Data
    with open('outputs/vrp_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1.5 Load Bases
    base_file = "data/tecnicos_internos.xlsx"
    base_map = {}
    if os.path.exists(base_file):
        df_base = pd.read_excel(base_file)
        try:
            df_base['tecnico'] = df_base['tecnico'].astype(str).str.strip()
            df_base['ciudad_base'] = df_base['ciudad_base'].astype(str).str.strip()
            base_map = dict(zip(df_base['tecnico'], df_base['ciudad_base']))
        except Exception as e:
            print(f"Warning: Could not read bases: {e}")
    
    # 2. Extract Events per Technician (Sorted by Day)
    tech_events = defaultdict(list)
    for entry in data.get('plan', []):
        if entry.get('type') != 'INTERNAL':
            continue
        tech = entry.get('tech')
        city = entry.get('city')
        day = entry.get('day')
        if tech and city and day:
            tech_events[tech].append({'day': day, 'city': city})

    # 3. Process Segments
    rows = []
    
    for tech, events in tech_events.items():
        # Sort by day
        events.sort(key=lambda x: x['day'])
        
        current_segment_city = None
        segment_days = []
        
        # Helper to flush segment
        def flush_segment(city, days_list):
            if not days_list: return
            
            start = min(days_list)
            end = max(days_list)
            span = end - start + 1
            active = len(days_list)
            gap = span - active
            
            # Check Lodging
            base = base_map.get(tech, "Santiago")
            is_lodging = (city != base and city != "Santiago") 
            # Note: Explicit 'Santiago' check if tech base is missing/ambiguous, but base_map.get handles default. 
            # Better relies on base_map. If Base=Santiago, City=Santiago -> No Lodging.
            is_lodging = (city != base)

            cost_lunch_active = active * 0.5
            cost_aloj_active = (active * 1.1) if is_lodging else 0.0
            
            gap_lunch = gap * 0.5
            gap_aloj = (gap * 1.1) if is_lodging else 0.0
            
            rows.append({
                "Tecnico": tech,
                "Ciudad": city,
                "Base": base,
                "Dia Inicio": start,
                "Dia Fin": end,
                "Duracion Calendario (Dias)": span,
                "Dias Activos (Pagados)": active,
                "Diferencia (Brecha)": gap,
                "Costo Almuerzos (UF)": cost_lunch_active,
                "Costo Alojamiento (UF)": cost_aloj_active,
                "Ahorro Almuerzo x Brecha (UF)": gap_lunch,
                "Ahorro Aloj x Brecha (UF)": gap_aloj,
                "Comentario": "Estadia Continua"
            })

        for e in events:
            d = e['day']
            c = e['city']
            
            if c != current_segment_city:
                # Segment Change
                if current_segment_city is not None:
                    flush_segment(current_segment_city, segment_days)
                current_segment_city = c
                segment_days = [d]
            else:
                # Continuity Check?
                # If there is a massive jump in days but SAME city (e.g. D1... D20), 
                # strictly speaking, if he didn't go anywhere else, it MIGHT be a gap.
                # But typically Solver assigns travel if he moves. 
                # If `plan` has no other city in between, he stayed there.
                segment_days.append(d)
        
        # Flush last
        if current_segment_city is not None:
            flush_segment(current_segment_city, segment_days)

    df_gaps = pd.DataFrame(rows)
    # Filter only meaningful gaps? Or show all? User wants "Logic result". 
    # Let's show all but maybe sort by Gap.
    df_gaps = df_gaps.sort_values(by=["Tecnico", "Dia Inicio"], ascending=[True, True])

    # 4. Parameters / Logic Explanation
    params_data = [
        {"Concepto": "Duracion Calendario", "Definicion": "Dias corridos desde que el tecnico llega hasta que se va."},
        {"Concepto": "Dias Activos (Pagados)", "Definicion": "Dias donde efectivamente se realiza trabajo (Instalacion GPS). Base del cobro de Almuerzos."},
        {"Concepto": "Diferencia (Brecha)", "Definicion": "Dias de estadia muerta (viajes, domingos, holguras) que NO se cobran como almuerzo/dia trabajo."},
        {"Concepto": "Costo Almuerzo", "Definicion": "0.5 UF por Dia Activo."},
        {"Concepto": "Costo Alojamiento", "Definicion": "1.1 UF por Noche (Solo si Ciudad != Base)."}
    ]
    df_params = pd.DataFrame(params_data)

    # 5. Write to Excel
    out_path = "outputs/reporte_brechas_dias_v2.xlsx"
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        df_gaps.to_excel(writer, sheet_name="Analisis Brechas y Costos", index=False)
        df_params.to_excel(writer, sheet_name="Explicacion Logica", index=False)
    
    print(f"Report generated: {out_path}")

if __name__ == "__main__":
    generate_report()
