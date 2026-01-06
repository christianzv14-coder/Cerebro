import pandas as pd
import os

OUTPUTS_DIR = "outputs"
excel_path = os.path.join(OUTPUTS_DIR, "plan_global_operativo.xlsx")

# Simulation of salary calculation
# From input file:
# ["Luis", "Santiago", 14.7, 1.0] -> 14.7 UF/month, 1.0 FTE.
# Project duration?
# The model calculates based on DAYS USED or MONTHLY prorated?
# Let's see the actual cost in Costos_Detalle.

def explain_costs():
    try:
        df_plan = pd.read_excel(excel_path, sheet_name="Plan_Diario")
        df_cost = pd.read_excel(excel_path, sheet_name="Costos_Detalle")
        
        # Load distance matrix for fuel example
        df_dist = pd.read_excel("data/matriz_distancia_km.xlsx", index_col=0)
        df_peaje = pd.read_excel("data/matriz_peajes.xlsx", index_col=0)
    except Exception as e:
        print(f"Error: {e}")
        return

    print("### 🔍 Explicación de Costos Unitarios \n")

    # 1. SUELDO BASE (Luis)
    # Check Luis row in Costos_Detalle
    luis_row = df_cost[df_cost["responsable"] == "Luis"].iloc[0]
    sueldo_luis = luis_row.get("sueldo_uf", luis_row.get("sueldo_proy_uf", 0))
    
    # How many days did Luis work or was assigned?
    # Logic in model: sueldo_proy = (sueldo_mes / 30) * dias_proyecto?
    # Or sueldo_mes * (weeks/4)?
    # Let's print the value to reverse engineer.
    print(f"**1. Sueldo Base (Caso: Luis)**")
    print(f"   - Sueldo Mensual Input: 14.7 UF")
    print(f"   - Costo Cargado al Proyecto: {sueldo_luis:.2f} UF")
    print(f"   * Explicación: El proyecto dura ~3.5-4 semanas. 14.7 * (24 días / 30) = ~11.76 UF.")
    print(f"   * Si el valor es {sueldo_luis:.2f}, entonces se pagó por los días exactos que duró la operación.\n")


    # 2. BENCINA Y PEAJE (Ejemplo: Santiago -> Rancagua)
    # Find a trip in Plan_Diario where Luis goes from Santiago to Rancagua?
    # Or Efrain goes Santiago -> San Antonio?
    
    # Let's look for a transition in Plan_Diario
    # day N: Santiago, day N+1: Rancagua
    
    # Just calculate hypothetical example based on matrices
    dist_stgo_rancagua = df_dist.loc["Santiago", "Rancagua"]
    peaje_stgo_rancagua = df_peaje.loc["Santiago", "Rancagua"]
    bencina_rate = 0.03
    fixed_per_trip = 0.13
    
    calc_bencina = dist_stgo_rancagua * bencina_rate
    total_trip = calc_bencina + peaje_stgo_rancagua + fixed_per_trip
    
    print(f"**2. Traslado (Ejemplo: Santiago -> Rancagua)**")
    print(f"   - Distancia: {dist_stgo_rancagua} km")
    print(f"   - Bencina ({bencina_rate} UF/km): {dist_stgo_rancagua} * {bencina_rate} = {calc_bencina:.2f} UF")
    print(f"   - Peaje (Matriz): {peaje_stgo_rancagua:.2f} UF")
    print(f"   - Costo Fijo (Imprevisto/Colación): {fixed_per_trip:.2f} UF")
    print(f"   - **Costo Total del Viaje:** {total_trip:.2f} UF")

if __name__ == "__main__":
    explain_costs()
