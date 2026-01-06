
import pandas as pd
import numpy as np

path = "outputs/plan_global_operativo.xlsx"
df_plan = pd.read_excel(path, sheet_name="Plan_Diario")
df_cost = pd.read_excel(path, sheet_name="Costos_Detalle")

print("=== DEEP AUDIT: ROW-BY-ROW ANALYSIS ===")

# 1. Check for Ping-Pong Travel (Inefficency)
print("\n[1] TRAVEL CONSISTENCY CHECK")
df_plan = df_plan.sort_values(["tecnico", "dia"])
df_plan["prev_city"] = df_plan.groupby("tecnico")["ciudad_trabajo"].shift(1)
df_plan["next_city"] = df_plan.groupby("tecnico")["ciudad_trabajo"].shift(-1)

# Flag if city changes A -> B -> A
switches = df_plan[
    (df_plan["prev_city"].notna()) & 
    (df_plan["prev_city"] != df_plan["ciudad_trabajo"]) &
    (df_plan["prev_city"] == df_plan["next_city"])
]
if not switches.empty:
    print("WARNING: 'Ping-Pong' travel detected (A->B->A in consecutive days):")
    print(switches[["tecnico", "dia", "prev_city", "ciudad_trabajo", "next_city"]])
else:
    print("OK: No immediate ping-pong travel detected.")

# 2. Check Daily Utilization (Are we maximizing the 8 hours?)
print("\n[2] DAILY UTILIZATION CHECK")
# Capacity per day = 8 hours approx (unless travel)
# Check days where gps_inst > 0 but hours_instal < 4 (Low utilization)
low_util = df_plan[
    (df_plan["gps_inst"] > 0) & 
    (df_plan["horas_instal"] < 4) &
    (df_plan["viaje_h_manana"] < 2) # Not due to long travel
]
if not low_util.empty:
    print("WARNING: Low utilization days detected (<4h work, no major travel):")
    print(low_util[["tecnico", "dia", "ciudad_trabajo", "horas_instal", "gps_inst", "viaje_h_manana"]])
else:
    print("OK: Daily utilization looks efficient.")

# 3. Salary vs Work Gap
print("\n[3] SALARY VS OUTPUT CHECK")
# Compare Avg Cost per GPS Internal vs External PxQ
internals = df_cost[df_cost["tipo"]=="INTERNO"]
total_int_cost = internals["total_uf"].sum()
total_int_gps = df_plan["gps_inst"].sum()
avg_cost_int = total_int_cost / total_int_gps if total_int_gps else 0

print(f"Internal Avg Cost/GPS: {avg_cost_int:.2f} UF")
print("External PxQ Ref (Santiago): ~2.7 UF ($108k) ?? No, wait.")
# We need to know what EXTERNAL cost is in UF for comparison
# Let's peek at Costos_Detalle for EXTERNO items
ext_rows = df_cost[df_cost["tipo"]=="EXTERNO"]
if not ext_rows.empty:
    # Estimate PxQ unitario promedio
    print("External PxQ breakdown by city (Top 5):")
    print(ext_rows.head(5)[["responsable", "total_uf", "pxq_uf"]])

# 4. Verify Local Transport Logic impact
print("\n[4] LOCAL TRANSPORT IMPACT")
# Check summing of 'viaje_h_manana' vs total vs travel cost
# travel_uf in Plan_Diario? No, it's in logic. Output excel Plan_Diario doesn't show cost column per row?
# We have to infer from Costos_Detalle.
print("Checking Costos_Detalle for Travel breakdown:")
print(internals[["responsable", "travel_uf", "sueldo_uf"]].head(10))

