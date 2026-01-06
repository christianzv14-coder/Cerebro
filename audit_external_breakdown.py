
import pandas as pd
import os

def audit_externals():
    file_path = os.path.join("outputs", "plan_global_operativo.xlsx")
    if not os.path.exists(file_path):
        print("File not found!")
        return

    try:
        df = pd.read_excel(file_path, "Costos_Detalle")
        print("\n--- COLUMNAS DETECTADAS ---")
        print(df.columns.tolist())
        
        # Identify relevant columns dynamically to avoid KeyError
        col_map = {c.lower().strip(): c for c in df.columns}
        
        tech_col = col_map.get("responsable", None)
        city_col = col_map.get("ciudad", None)
        # Try to find 'gps_inst' column
        qty_col = col_map.get("gps_inst", None) or col_map.get("gps_asignados", None)
        
        type_col = col_map.get("tipo", None)
        
        if not type_col:
             print("ERROR: Columna 'tipo' no encontrada.")
             return

        # Filter Externals by TYPE
        externals = df[df[type_col].astype(str).str.upper() == "EXTERNO"]
        
        if externals.empty:
            print("No external costs found (by Type).")
            return

        print(f"\n--- DESGLOSE DE LOS 731 UF (EXTERNOS) ---")
        # For Externals, 'responsable' holds the City Name
        # 'gps_inst' holds the Quantity
        # Simplify output to avoid terminal truncation
        cols_to_show = [tech_col, qty_col, "total_uf"]
        # Rename for clarity
        renamed = externals[cols_to_show].rename(columns={tech_col: "Ciudad", qty_col: "Qty", "total_uf": "Costo (UF)"})
        
        print(renamed.to_string(index=False))
        
        # Verify Sum
        total_pxq = externals[pxq_col].sum() if pxq_col else 0
        total_flete = externals[flete_col].sum() if flete_col else 0
        print(f"\nSUMA CHECK: {total_pxq + total_flete:.2f} UF")
        
    except Exception as e:
        print(f"Error reading excel: {e}")

if __name__ == "__main__":
    audit_externals()
