import pandas as pd
import os

OUTPUTS_DIR = "outputs"
excel_path = os.path.join(OUTPUTS_DIR, "plan_global_operativo.xlsx")

def main():
    try:
        df_plan = pd.read_excel(excel_path, sheet_name="Plan_Diario")
        df_city = pd.read_excel(excel_path, sheet_name="Costos_por_Ciudad")
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    # 1. Group Internals by City
    # df_plan columns: tecnico, dia, ciudad_trabajo, gps_inst, ...
    # Filter where gps_inst > 0 to see who actually worked there (or just visited? user said "operan")
    # Let's include if they installed GPS.
    
    city_techs = {}

    # Get all unique cities from the report
    all_cities = df_city["ciudad"].unique()
    
    for c in all_cities:
        city_techs[c] = set()

    # Process Internals
    # Filter for rows where some work was done or assigned
    worked = df_plan[df_plan["ciudad_trabajo"].notna()]
    
    for _, row in worked.iterrows():
        c = row["ciudad_trabajo"]
        t = row["tecnico"]
        gps = row.get("gps_inst", 0)
        # If they are there, they are "operating" even if just resting or traveling to?
        # User likely means "who is assigned to this city".
        # Let's count them if they appear in the plan for that city.
        if c in city_techs:
            city_techs[c].add(t)
    
    # Process Externals
    # df_city columns: ciudad, gps_externos
    
    ext_counter = 1
    
    print("\n### 📍 Técnicos por Ciudad")
    print("| Ciudad | Técnicos Asignados (Internos + Externos) |")
    print("| :--- | :--- |")
    
    # Sort cities alphabetically
    sorted_cities = sorted(all_cities)
    
    for c in sorted_cities:
        techs = sorted(list(city_techs.get(c, set())))
        
        # Check externals
        row = df_city[df_city["ciudad"] == c]
        if not row.empty:
            ext_gps = row.iloc[0]["gps_externos"]
            if ext_gps > 0:
                # "los tecnicos externos numeralos del 1 al n nomas"
                # Does user mean unique ID globally or per city? 
                # "Externo 1", "Externo 2" globally? Or just "Externo"?
                # Usually implies distinct entities. Let's use a global counter or per city?
                # "numeralos del 1 al n". I'll format as "Externo N"
                techs.append(f"Externo {ext_counter}")
                ext_counter += 1
        
        tech_str = ", ".join(techs) if techs else "Sin asignación"
        print(f"| {c} | {tech_str} |")

if __name__ == "__main__":
    main()
