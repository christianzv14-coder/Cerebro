
import pandas as pd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = "outputs/plan_global_operativo.xlsx"
df_plan = pd.read_excel(path, sheet_name="Plan_Diario")

# Sort by Technician and Day
df_plan = df_plan.sort_values(["tecnico", "dia"])

print("=== RUTAS DE TÉCNICOS INTERNOS ===")

for tech, group in df_plan.groupby("tecnico"):
    print(f"\n👷 TÉCNICO: {tech}")
    
    current_city = None
    start_day = None
    last_day = None
    gps_count = 0
    
    itinerary = []
    
    for _, row in group.iterrows():
        city = row["ciudad_trabajo"]
        day = row["dia"]
        gps = row["gps_inst"]
        
        if city != current_city:
            if current_city is not None:
                itinerary.append(f"  📍 {current_city}: Días {start_day}-{last_day} ({gps_count} GPS)")
            
            current_city = city
            start_day = day
            gps_count = gps
        else:
            gps_count += gps
        
        last_day = day
    
    # Append the last segment
    if current_city is not None:
        itinerary.append(f"  📍 {current_city}: Días {start_day}-{last_day} ({gps_count} GPS)")
        
    for leg in itinerary:
        print(leg)
