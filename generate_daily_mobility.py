
import json
import pandas as pd
import os

def generate_mobility_report():
    # Constants
    UF_VALUE = 39500.0
    DAILY_COST_CLP = 5000.0
    DAILY_COST_UF = DAILY_COST_CLP / UF_VALUE
    
    with open('outputs/vrp_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    rows = []
    
    # Iterate all internal events
    # We want one entry per Active Day per Technician
    
    # We need to deduplicate if a tech has multiple events in same day?
    # Usually 'plan' has one event per tech per day?
    # Let's check: The VRP result structure usually lists distinct events.
    # If a tech works in morning and afternoon, is it 1 'day'?
    # It identifies by "day". So we group by (Tech, Day).
    
    events = []
    for entry in data.get('plan', []):
        if entry.get('type') == 'INTERNAL':
            events.append(entry)
            
    # Use a set to track unique tech-days
    processed_days = set()
    
    sorted_events = sorted(events, key=lambda x: (x['tech'], x['day']))
    
    for e in sorted_events:
        tech = e['tech']
        day = e['day']
        city = e['city']
        
        key = (tech, day)
        if key in processed_days:
            continue
            
        processed_days.add(key)
        
        rows.append({
            "Tecnico": tech,
            "Dia": day,
            "Ciudad": city,
            "Concepto": "Traslado Interno (Movilizacion)",
            "Monto (CLP)": DAILY_COST_CLP,
            "Valor UF Ref": UF_VALUE,
            "Costo (UF)": DAILY_COST_UF
        })
        
    df = pd.DataFrame(rows)
    
    # Summary
    print(f"Total Rows: {len(df)}")
    if not df.empty:
        total_uf = df["Costo (UF)"].sum()
        print(f"Total Cost (UF): {total_uf:.4f}")

    out_path = "outputs/reporte_movilizacion_diaria.xlsx"
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
        
    print(f"Report generated: {out_path}")

if __name__ == "__main__":
    generate_mobility_report()
