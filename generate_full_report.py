
import pandas as pd
import os

# Forced cities list for commenting
FORCED = ["Arica", "Punta Arenas", "Coyhaique"]

def generate_report():
    file_path = os.path.join("outputs", "plan_global_operativo.xlsx")
    if not os.path.exists(file_path):
        print("File not found.")
        return

    # Check 'Costos_por_Ciudad' sheet first
    try:
        df_city = pd.read_excel(file_path, "Costos_por_Ciudad")
        # Columns likely: ciudad, gps_total, gps_internos, gps_externos, total_ciudad_uf...
        
        # We also need WHO did it. 
        # But 'Costos_por_Ciudad' might just summarize Qty.
        # 'Plan_Diario' has the Technician assignment.
        df_plan = pd.read_excel(file_path, "Plan_Diario")
        
        # Aggregate Plan to find Techs per City
        # Filter where gps_inst > 0
        df_plan = df_plan[df_plan['gps_inst'] > 0]
        techs_per_city = df_plan.groupby('ciudad_trabajo')['tecnico'].unique().apply(list).to_dict()
        
        # Build Report
        report_rows = []
        for idx, row in df_city.iterrows():
            city = row['ciudad']
            qty_total = row['gps_total']
            qty_ext = row['gps_externos']
            qty_int = row['gps_internos']
            cost = row['total_ciudad_uf']
            
            # Determine Techs
            techs = techs_per_city.get(city, [])
            tech_str = ", ".join(techs)
            
            if qty_ext > 0:
                if tech_str:
                    tech_str += f", Externo ({qty_ext})"
                else:
                    tech_str = f"Externo ({qty_ext})"
            
            # Logic for Comment
            comment = ""
            if qty_ext > 0:
                if city in FORCED:
                    comment = "✅ Externalizado (Regla)"
                else:
                    comment = "⚠️ Overflow (Ineficiencia)"
            else:
                comment = "✅ Interno (Eficiente)"
                
            report_rows.append({
                "Ciudad": city,
                "Técnicos": tech_str,
                "Q": qty_total,
                "Costo (UF)": round(cost, 2),
                "Comentario": comment
            })
            
        # Create DF
        final_df = pd.DataFrame(report_rows)
        # Sort by Cost Descending
        final_df = final_df.sort_values("Costo (UF)", ascending=False)
        
        # Custom MD Table output to avoid tabulate dependency
        md_lines = []
        headers = final_df.columns.tolist()
        md_lines.append("| " + " | ".join(headers) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        for _, row in final_df.iterrows():
            line = "| " + " | ".join(str(row[col]) for col in headers) + " |"
            md_lines.append(line)
            
        output_file = os.path.join("outputs", "full_city_report.md")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
            
        print(f"Report saved to {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    generate_report()
