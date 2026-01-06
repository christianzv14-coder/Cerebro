import pandas as pd
import os

OUTPUTS_DIR = "outputs"
excel_path = os.path.join(OUTPUTS_DIR, "plan_global_operativo.xlsx")

def print_cost_summary():
    try:
        df_det = pd.read_excel(excel_path, sheet_name="Costos_Detalle")
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    # Categorize costs
    summary = {
        "Mano de Obra Interna (Sueldo Base)": df_det["sueldo_uf"].sum(),
        "Incentivos Variables (Producción)": df_det["inc_uf"].sum(),
        "Viáticos (Alojamiento + Alimentación)": df_det["aloj_uf"].sum() + df_det["alm_uf"].sum(),
        "Traslados Regiones (Pasajes + Flete + Peaje)": df_det["travel_uf"].sum() + df_det["flete_uf"].sum(),
        "Traslados Internos (Diario $5k)": df_det.get("traslado_interno_uf", pd.Series([0]*len(df_det))).sum(),
        "Servicios Externos (Overflow)": df_det["pxq_uf"].sum(),
        "Materiales (Kits GPS)": df_det["materiales_uf"].sum()
    }

    # Total check
    total_calculated = sum(summary.values())
    
    print("\n### 💰 Desglose de Costos del Proyecto")
    print("| Ítem de Costo | Monto (UF) | % del Total |")
    print("| :--- | :--- | :--- |")
    
    for item, amount in summary.items():
        pct = (amount / total_calculated * 100) if total_calculated > 0 else 0
        print(f"| {item} | **{amount:,.2f} UF** | {pct:.1f}% |")
        
    print(f"| **TOTAL FINAL** | **{total_calculated:,.2f} UF** | **100%** |")

if __name__ == "__main__":
    print_cost_summary()
