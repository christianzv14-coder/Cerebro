
import pandas as pd
import os

path = "outputs/plan_global_operativo.xlsx"

try:
    df_cost = pd.read_excel(path, sheet_name="Costos_Detalle")
    print("--- TOTAL COST BREAKDOWN ---")
    print(df_cost.groupby("tipo")["total_uf"].sum())
    
    print("\n--- TOP 5 EXPENSIVE ITEMS ---")
    print(df_cost.sort_values("total_uf", ascending=False).head(10)[["responsable", "tipo", "total_uf", "travel_uf", "pxq_uf", "materiales_uf"]])

    print("\n--- MATERIAL COST CHECK ---")
    mat_cost = df_cost[df_cost["tipo"]=="MATERIALES"]["total_uf"].sum()
    print(f"Material Total: {mat_cost:.2f}")
    
    print("\n--- INTERNAL STATS ---")
    internals = df_cost[df_cost["tipo"]=="INTERNO"]
    print(f"Internal Total: {internals['total_uf'].sum():.2f}")
    print(f"Internal Travel: {internals['travel_uf'].sum():.2f}")
    print(f"Internal Salaries: {internals['sueldo_uf'].sum():.2f}")
    
    print("\n--- EXTERNAL STATS ---")
    externals = df_cost[df_cost["tipo"]=="EXTERNO"]
    print(f"External Total: {externals['total_uf'].sum():.2f}")
    print(f"External PxQ: {externals['pxq_uf'].sum():.2f}")

except Exception as e:
    print(f"Error reading breakdown: {e}")
