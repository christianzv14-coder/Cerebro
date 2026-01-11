
import pandas as pd
import os

os.makedirs('data', exist_ok=True)

data = [
    {'fecha': '2024-01-01', 'tipo_actividad': 'INSTALACION', 'cantidad_actividad': 10},
    {'fecha': '2024-01-02', 'tipo_actividad': 'RETIRO', 'cantidad_actividad': 5},
    {'fecha': '2024-01-08', 'tipo_actividad': 'REVISION', 'cantidad_actividad': 2},
]

df = pd.DataFrame(data)
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'input_actividades.xlsx')
df.to_excel(OUTPUT_FILE, index=False)
print(f"Template created: {OUTPUT_FILE}")
