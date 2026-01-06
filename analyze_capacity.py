
import pandas as pd
import math

path = "outputs/plan_global_operativo.xlsx"
df_plan = pd.read_excel(path, sheet_name="Plan_Diario")
df_techs = pd.read_excel("data/tecnicos_internos.xlsx")
df_params = pd.read_excel("data/parametros.xlsx")
cols_param = df_params.set_index("parametro")["valor"].to_dict()

# Constants
DIAS_SEM = float(cols_param.get("dias_semana", 6.0))
SEMANAS = float(cols_param.get("semanas_proyecto", 4.0))
DIAS_MAX_TOTAL = DIAS_SEM * SEMANAS # 24 aprox

print("=== ANÁLISIS DE CAPACIDAD ===")

stats = []

for _, row in df_techs.iterrows():
    tech = row["tecnico"]
    fte = float(row["hh_semana_proyecto"]) # This column holds FTE in our new logic? Wait, let me check generate_inputs code.
    # In generate_inputs: ["Luis", "Santiago", 14.7, 0.75] -> hh_semana_proyecto = 0.75
    
    # Days Available Logic from model: floor(FTE * DIAS_MAX_TOTAL)
    dias_disp = math.floor(fte * DIAS_MAX_TOTAL)
    
    # Days Worked from Plan
    days_worked = df_plan[df_plan["tecnico"] == tech]["dia"].nunique()
    gps_installed = df_plan[df_plan["tecnico"] == tech]["gps_inst"].sum()
    
    utilization = (days_worked / dias_disp) * 100 if dias_disp > 0 else 0
    
    stats.append({
        "Técnico": tech,
        "Base": row["ciudad_base"],
        "FTE": fte,
        "Días Disp": dias_disp,
        "Días Trab": days_worked,
        "GPS Total": gps_installed,
        "% Ocupación": round(utilization, 1)
    })

df_res = pd.DataFrame(stats)
print(df_res.to_string(index=False))

print("\n--- RESUMEN ---")
print(f"Total Días Disponibles: {df_res['Días Disp'].sum()}")
print(f"Total Días Trabajados: {df_res['Días Trab'].sum()}")
print(f"Holgura (Días libres): {df_res['Días Disp'].sum() - df_res['Días Trab'].sum()}")
