import pandas as pd
import os

OUTPUTS_DIR = "outputs"
excel_path = os.path.join(OUTPUTS_DIR, "plan_global_operativo.xlsx")

# Constants used in model
VALOR_KIT = 4.40
VALOR_INCENTIVO = 1.04
VALOR_HOTEL = 1.1
VALOR_ALMUERZO = 0.5
VALOR_BENCINA_KM = 0.03
# Fletes vary, so we'll calc average
# Externals vary, so we'll calc average

def main():
    try:
        df_plan = pd.read_excel(excel_path, sheet_name="Plan_Diario")
        df_cost = pd.read_excel(excel_path, sheet_name="Costos_Detalle")
        df_ext = pd.read_excel(excel_path, sheet_name="Costos_por_Ciudad")
        df_flete = pd.read_excel(excel_path, "Fletes_Detalle") if "Fletes_Detalle" in pd.ExcelFile(excel_path).sheet_names else None
        # Fletes might be aggregated in cost detail, let's allow for missing sheet
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return
    
    # 1. MATERIALES
    total_gps = 314 # Fixed assumption or sum?
    total_gps_external = df_ext["gps_externos"].sum() if not df_ext.empty else 0
    total_gps_internal = df_plan["gps_inst"].sum()
    
    # Check consistency
    total_gps_calc = total_gps_internal + total_gps_external
    
    cost_materiales = total_gps_calc * VALOR_KIT
    
    # 2. MO INTERNA
    # Sueldo Base (Total from Costos_Detalle)
    # This is fixed/prorated, not purely unitary.
    # Note: Column name might be sueldo_uf based on print_cost_table.py
    if "sueldo_uf" in df_cost.columns:
        total_sueldo_base = df_cost["sueldo_uf"].sum()
    elif "sueldo_proy_uf" in df_cost.columns:
        total_sueldo_base = df_cost["sueldo_proy_uf"].sum()
    else:
        # Fallback or error? Maybe calculate manual?
        total_sueldo_base = 0
        print("Warning: sueldo column not found")
    
    # Incentivos
    total_incentivos = df_cost["inc_uf"].sum()
    qty_incentivos = total_gps_internal # Should match exactly
    
    # 3. LOGISTICA
    # Alojamiento (Reverse engineer quantity)
    total_aloj = df_cost["aloj_uf"].sum()
    qty_noches = round(total_aloj / VALOR_HOTEL) if VALOR_HOTEL > 0 else 0
    
    # Alimentacion
    total_alm = df_cost["alm_uf"].sum()
    qty_dias_alm = round(total_alm / VALOR_ALMUERZO) if VALOR_ALMUERZO > 0 else 0
    
    # Transporte (Bencina + Peajes + Fixed)
    total_travel = df_cost["travel_uf"].sum()
    # It's hard to split Bencina vs Peajes without logs, so we report as "Global"
    
    # 4. EXTERNOS
    # pxq_uf is the service cost. flete_uf is separated below.
    total_ext_cost = df_ext["pxq_uf"].sum() if not df_ext.empty else 0
    avg_ext_unit = (total_ext_cost / total_gps_external) if total_gps_external > 0 else 0
    
    # 5. FLETES
    # Flete is in Costos_Detalle 'flete_uf' column?
    total_flete = df_cost["flete_uf"].sum()
    # Also need to add external freight which might be in Costos_por_Ciudad 'flete_uf'?
    if not df_ext.empty and "flete_uf" in df_ext.columns:
         total_flete += df_ext["flete_uf"].sum()

    # Create Table Data
    rows = []
    
    # Format: [Categoria, Item, Cantidad, Unidad, Costo Unitario, Total UF]
    
    rows.append(["Materiales", "Kits GPS", int(total_gps_calc), "Unid.", f"{VALOR_KIT:.2f}", f"{cost_materiales:.2f}"])
    
    rows.append(["Mano de Obra (Int)", "Sueldo Base (Fijo)", 7, "Técnicos", "Var.", f"{total_sueldo_base:.2f}"])
    rows.append(["Mano de Obra (Int)", "Incentivo Producción", int(qty_incentivos), "GPS Inst.", f"{VALOR_INCENTIVO:.2f}", f"{total_incentivos:.2f}"])
    
    rows.append(["Logística (Int)", "Alojamiento (Hotel)", int(qty_noches), "Noches", f"{VALOR_HOTEL:.2f}", f"{total_aloj:.2f}"])
    rows.append(["Logística (Int)", "Alimentación (Viático)", int(qty_dias_alm), "Días", f"{VALOR_ALMUERZO:.2f}", f"{total_alm:.2f}"])
    rows.append(["Logística (Int)", "Combustible y Peajes", 1, "Global", "Var.", f"{total_travel:.2f}"])
    
    rows.append(["Servicios Externos", "Instalación Overflow", int(total_gps_external), "GPS Inst.", f"{avg_ext_unit:.2f} (Prom)", f"{total_ext_cost:.2f}"])
    
    rows.append(["Logística (Misc)", "Fletes / Encomiendas", 1, "Global", "Var.", f"{total_flete:.2f}"])
    
    grand_total = cost_materiales + total_sueldo_base + total_incentivos + total_aloj + total_alm + total_travel + total_ext_cost + total_flete
    
    # Print Table
    print(f"\n### Detalle de Costos Unitarios y Totales")
    print(f"| Categoría | Ítem | Cantidad | Unidad | Costo Unitario (UF) | Total (UF) |")
    print(f"| :--- | :--- | :--- | :--- | :--- | :--- |")
    for r in rows:
        print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
    print(f"| **TOTAL** | **PROYECTO COMPLETO** | **314** | **GPS** | **{grand_total/314:.2f}** | **{grand_total:.2f}** |")

if __name__ == "__main__":
    main()
