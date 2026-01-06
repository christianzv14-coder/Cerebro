
import json
import pandas as pd
import os

def check_totals():
    # Load Result
    with open('outputs/vrp_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Load Bases
    base_file = "data/tecnicos_internos.xlsx"
    if not os.path.exists(base_file):
        print(f"Error: {base_file} not found.")
        return

    df_base = pd.read_excel(base_file)
    # Expected columns: tecnico, ciudad_base
    # Normalize names if needed (stripped)
    try:
        df_base['tecnico'] = df_base['tecnico'].astype(str).str.strip()
        df_base['ciudad_base'] = df_base['ciudad_base'].astype(str).str.strip()
        base_map = dict(zip(df_base['tecnico'], df_base['ciudad_base']))
    except KeyError:
        print("Columns 'tecnico' or 'ciudad_base' missing in Excel.")
        return

    total_almuerzos = 0
    total_alojamientos = 0
    
    # We aggregate unique (Tech, Day) to avoid double counting if multiple entries per day exist (rare but possible in solver output structure?)
    # The JSON 'plan' usually has One entry per day-tech? Or multiple if multiple activities?
    # Solver constraint 'unica' implies one location per day.
    # But let's be safe: Set of (Tech, Day).
    
    unique_days = set()


def check_totals_excel():
    excel_path = "outputs/reporte_costos_Final_Revertido.xlsx"
    if not os.path.exists(excel_path):
        print("Excel report not found.")
        return

    df = pd.read_excel(excel_path, sheet_name="Detalle Costos")
    
    # Sum Columns
    # 'Almuerzos' is in UF. Unit Cost = 0.5
    # 'Alojamientos' is in UF. Unit Cost = 1.1
    
    total_almuerzo_uf = df['Almuerzos'].sum()
    total_aloj_uf = df['Alojamientos'].sum()
    
    count_almuerzos = total_almuerzo_uf / 0.5
    count_aloj = total_aloj_uf / 1.1
    
    print(f"--- FROM EXCEL REPORT ---")
    print(f"Total Cost Almuerzos (UF): {total_almuerzo_uf:.2f}")
    print(f"Estimated Count Almuerzos (Cost/0.5): {count_almuerzos:.1f}")
    print(f"Total Cost Alojamientos (UF): {total_aloj_uf:.2f}")
    print(f"Estimated Count Alojamientos (Cost/1.1): {count_aloj:.1f}")

if __name__ == "__main__":
    # check_totals() # Skip JSON check
    check_totals_excel()
