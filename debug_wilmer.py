
import modelo_optimizacion_gps_chile_v1 as model

print("DEBUG: Checking Wilmer")
try:
    days = model.dias_disponibles_proyecto("Wilmer")
    fte = model.fte_tecnico("Wilmer")
    print(f"Wilmer Days: {days}")
    print(f"Wilmer FTE: {fte}")
except Exception as e:
    print(f"Error: {e}")
    
# Check raw data from Excel used by model
print("Raw Excel Data:")
import pandas as pd
df = pd.read_excel("data/tecnicos_internos.xlsx")
row = df[df['tecnico'] == 'Wilmer']
print(row[['tecnico', 'hh_semana_proyecto']].to_string())
