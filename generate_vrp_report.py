
import json
import pandas as pd
import os
import modelo_optimizacion_gps_chile_v1 as shared

def generate_md_report():
    json_path = "outputs/vrp_result.json"
    if not os.path.exists(json_path):
        print("JSON result not found.")
        return

    with open(json_path, "r") as f:
        data = json.load(f)

    lines = []
    lines = []
    lines.append("# 🚀 Reporte Final de Optimización (VRP Nuclear)")
    
    # --- COST BREAKDOWN ---
    total_uf = data['cost_total']
    op_uf = data['cost_operational']
    mat_uf = data['cost_materials']
    
    # Recalculate component parts for breakdown
    # 1. Salaries
    total_salaries = sum(shared.costo_sueldo_proyecto_uf(t) for t in shared.TECNICOS)
    
    # 2. External
    external_cost = 0.0
    for item in data['plan']:
        if item['type'] == 'EXTERNAL':
             # We need to re-calc unit cost here or infer? 
             # Let's use shared function
             c = item['city']
             qty = item['gps']
             vals = shared.costo_externo_uf(c, qty)
             external_cost += vals["total_externo_sin_materiales_uf"]
             
    # 3. Incentives
    gt_internal = sum(x['gps'] for x in data['plan'] if x['type'] == 'INTERNAL')
    incentive_cost = gt_internal * shared.INCENTIVO_UF
    
    # 4. Logistics (The Rest)
    # Op Cost = Salaries + Ext + Inc + Logistics
    logistics_cost = op_uf - (total_salaries + external_cost + incentive_cost)
    
    lines.append("## 💰 Desglose de Costos (Detallado)")
    lines.append("| Ítem | Costo (UF) | % del Total |")
    lines.append("| :--- | :--- | :--- |")
    
    def add_row(name, val):
        pct = (val / total_uf) * 100
        lines.append(f"| {name} | {val:.2f} | {pct:.1f}% |")
        
    add_row("👷 Sueldos (Fijo)", total_salaries)
    add_row("📦 Materiales (Fijo)", mat_uf)
    add_row("🚌 Logística (Viajes/Hotel/Alm)", logistics_cost)
    add_row("🤝 Externalización", external_cost)
    add_row("🎁 Incentivos (Producción)", incentive_cost)
    lines.append(f"| **TOTAL** | **{total_uf:.2f}** | **100%** |")
    
    lines.append("\n---")

    # --- GANTT CHART ---
    lines.append("## 📊 Diagrama de Gantt (Flujo de Movimiento)")
    lines.append("Visualización de dónde está cada técnico día a día.")
    lines.append("```mermaid")
    lines.append("gantt")
    lines.append("    title 🗓️ Planificación 24 Días")
    lines.append("    dateFormat YYYY-MM-DD")
    lines.append("    axisFormat %d")
    
    full_plan = [x for x in data['plan'] if x['type'] == 'INTERNAL']
    df_plan = pd.DataFrame(full_plan)
    techs = df_plan['tech'].unique()
    
    # Base Date: Day 1 = 2024-03-01
    from datetime import date, timedelta
    start_date = date(2024, 3, 1)
    
    for t in techs:
        lines.append(f"    section {t}")
        t_data = df_plan[df_plan['tech'] == t].sort_values('day')
        
        # We need to fill gaps with 'Base' to make continuous blocks?
        # Or just plot what we have.
        # Plotting contiguous blocks is cleaner.
        
        # Create full timeline list
        timeline = []
        base_t = shared.base_tecnico(t)
        day_map = {row['day']: row['city'] for _, row in t_data.iterrows()}
        
        current_city = base_t # Day 0
        current_start_day = 0
        
        # Iterate 1..24
        for d in range(1, 26): # Go to 25 to close last block
            if d <= 24:
                city = day_map.get(d, base_t) # Default to Base if gap
            else:
                city = "END" # Sentinel
            
            if city != current_city:
                # Close block
                # Determine state
                state = "active" if current_city != base_t else "done" # Done=Base, Active=Deploy
                
                # Mermaid Date
                d_date = start_date + timedelta(days=current_start_day-1) 
                # Note: Day 0 is virtual. Let's map Day 1 -> 2024-03-01.
                # If block starts at 0? 
                if current_start_day == 0:
                     # Just show as milestone or skip?
                     # Let's verify. Day 1 is index 0 for date.
                     d_date_str = d_date.strftime("%Y-%m-%d")
                else:
                     d_date_str = (start_date + timedelta(days=current_start_day-1)).strftime("%Y-%m-%d")

                length = d - current_start_day
                if length > 0 and current_city != "END":
                     # Sanitize City Name for Mermaid (remove spaces?)
                     safe_city = current_city.replace(" ", "_")
                     # If Base, maybe simpler color?
                     # Syntax: Label :state, id, start, len
                     lines.append(f"    {current_city} :{state}, {d_date_str}, {length}d")
                
                current_city = city
                current_start_day = d
                
    lines.append("```")
    lines.append("\n---")
    
    # 1. External Assignments
    lines.append("## 📦 Asignaciones Externas (Overflow)")
    externals = [x for x in data['plan'] if x['type'] == 'EXTERNAL']
    if externals:
        df_ext = pd.DataFrame(externals)
        grouped = df_ext.groupby('city')['gps'].sum().reset_index()
        lines.append("| Ciudad | Cantidad (GPS) |")
        lines.append("| :--- | :--- |")
        for _, row in grouped.iterrows():
             lines.append(f"| {row['city']} | {row['gps']} |")
    else:
        lines.append("No hay asignaciones externas.")
 
    lines.append("\n---")

    # 2. Tech Itineraries
    lines.append("## 📅 Itinerario Detallado por Técnico")
    
    full_plan = [x for x in data['plan'] if x['type'] == 'INTERNAL']
    df_plan = pd.DataFrame(full_plan)
    
    techs = df_plan['tech'].unique()
    
    for t in techs:
        lines.append(f"\n### 👷 {t}")
        t_data = df_plan[df_plan['tech'] == t].sort_values('day')
        
        lines.append("| Día | Ciudad | Actividad (GPS Inst) |")
        lines.append("| :--- | :--- | :--- |")
        
        # Day 0: Start at Base
        base_t = shared.base_tecnico(t)
        prev_city = base_t
        lines.append(f"| 0 | {base_t} | 🏠 Inicio en Base |")
        
        # Fill full timeline 1..24
        
        # Convert to dict for easy lookup
        day_map = {}
        for _, row in t_data.iterrows():
            day_map[row['day']] = row
            
        full_days = range(1, 25) # 1 to 24
        
        for d in full_days:
            # Current State
            if d in day_map:
                row = day_map[d]
                c = row['city']
                g = row['gps']
            else:
                c = base_t
                g = 0
            
            note = ""
            if prev_city and c != prev_city:
                # Detect Mode
                c_land = shared.costo_viaje_uf(prev_city, c, "terrestre")
                c_air = shared.costo_viaje_uf(prev_city, c, "avion")
                
                if c_air < 0.1: c_air = 999999.0
                
                if c_air < c_land:
                     mode_icon = "✈️ (Avión)"
                else:
                     mode_icon = "🚛 (Terrestre)"
                
                note = f"{mode_icon} Viaje desde {prev_city}"
            
            if g == 0:
                if not note: 
                    if c == base_t:
                        note = "🏠 En Base (Disponible)"
                    else:
                        note = "🛌 Descanso / Traslado"
            else:
                work_note = f"🛠️ Instala {g}"
                note = f"{note} <br> {work_note}" if note else work_note
                
            lines.append(f"| {d} | {c} | {note} |")
            prev_city = c

    with open("outputs/final_vrp_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Report generated: outputs/final_vrp_report.md")

if __name__ == "__main__":
    generate_md_report()
