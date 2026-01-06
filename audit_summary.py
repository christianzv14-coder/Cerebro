
import pandas as pd
path = "outputs/plan_global_operativo.xlsx"
df_plan = pd.read_excel(path, sheet_name="Plan_Diario")
df_cost = pd.read_excel(path, sheet_name="Costos_Detalle")

cost_ext = df_cost[df_cost["tipo"]=="EXTERNO"]["total_uf"].sum()
cost_int_sal = df_cost[df_cost["tipo"]=="INTERNO"]["sueldo_uf"].sum()
cost_int_trav = df_cost[df_cost["tipo"]=="INTERNO"]["travel_uf"].sum()
cost_mat = df_cost[df_cost["tipo"]=="MATERIALES"]["total_uf"].sum()

trips = df_plan[df_plan["viaje_h_manana"] > 0].shape[0]
gps_int = df_plan["gps_inst"].sum()

print(f"EXTERNO TOTAL: {cost_ext}")
print(f"SALARIO INT: {cost_int_sal}")
print(f"TRAVEL INT (inc local): {cost_int_trav}")
print(f"MAT TOTAL: {cost_mat}")
print(f"TOTAL TRIPS: {trips}")
print(f"GPS INTERNAL: {gps_int}")
