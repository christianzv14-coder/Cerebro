
import pandas as pd
import math

path = "outputs/plan_global_operativo.xlsx"
COSTO_KIT = 3.19
TRASLADO_LOCAL = 1.3
HOURS_OLD = 7
HOURS_NEW = 8
INSTALL_TIME = 2.5

print(f"--- AUDITING: {path} ---")

try:
    df_plan = pd.read_excel(path, sheet_name="Plan_Diario")
    df_cost = pd.read_excel(path, sheet_name="Costos_Detalle")
    
    # 1. Check Productivity (GPS per day)
    print("\n[1] PRODUCTIVITY CHECK")
    install_days = df_plan[df_plan["gps_inst"] > 0]
    avg_gps = install_days["gps_inst"].mean() if not install_days.empty else 0
    max_gps = install_days["gps_inst"].max() if not install_days.empty else 0
    print(f"Avg GPS/Day (Active): {avg_gps:.2f}")
    print(f"Max GPS/Day: {max_gps} (Expected: {math.floor(HOURS_NEW/INSTALL_TIME)})")
    
    # 2. Check Labor Efficiency
    print("\n[2] LABOR EFFICIENCY")
    total_gps = df_plan["gps_inst"].sum()
    total_days = df_plan["dia"].count() 
    print(f"Total GPS Installed (Internal): {total_gps}")
    print(f"Total Technician Days: {total_days}")
    print(f"Global Avg GPS/Day: {total_gps/total_days if total_days else 0:.2f}")

    # 3. Cost Breakdown Analysis
    print("\n[3] COST DRIVERS (INTERNOS)")
    internals = df_cost[df_cost["tipo"]=="INTERNO"]
    
    sueldo_total = internals["sueldo_uf"].sum()
    viaje_total = internals["travel_uf"].sum() 
    aloj_total = internals["aloj_uf"].sum()
    viatico_total = internals["alm_uf"].sum()
    
    print(f"Total Salary: {sueldo_total:.2f}")
    print(f"Total Travel (inc local): {viaje_total:.2f}")
    print(f"Total Lodging: {aloj_total:.2f}")
    print(f"Total Food: {viatico_total:.2f}")
    
    est_local_transport = total_days * TRASLADO_LOCAL
    print(f"Est. Local Transport (1.3 * Days): {est_local_transport:.2f}")
    print(f"Travel (Inter-city only approx): {viaje_total - est_local_transport:.2f}")

    # 4. Tech Performance
    print("\n[4] TECHNICIAN PERFORMANCE")
    tech_grp = df_plan.groupby("tecnico").agg(
        days=("dia", "count"),
        gps=("gps_inst", "sum"),
        cities=("ciudad_trabajo", "nunique")
    )
    tech_grp["gps_per_day"] = tech_grp["gps"] / tech_grp["days"]
    print(tech_grp)

    # 5. External Costs
    print("\n[5] EXTERNAL COSTS")
    externals = df_cost[df_cost["tipo"]=="EXTERNO"]
    print(f"External Total: {externals['total_uf'].sum():.2f}")
    print(f"External PxQ: {externals['pxq_uf'].sum():.2f}")
    
    # 6. Travel Intensity
    print("\n[6] TRAVEL INTENSITY")
    trips = df_plan[df_plan["viaje_h_manana"] > 0]["dia"].count()
    print(f"Total Inter-City Trips: {trips}")
    print(f"Avg Trips/Tech: {trips / df_plan['tecnico'].nunique() if not df_plan.empty else 0:.1f}")

except Exception as e:
    print(f"Error reading file: {e}")
