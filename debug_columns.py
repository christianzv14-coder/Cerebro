
import pandas as pd

try:
    df = pd.read_excel('costo_operativo_rabie_PRUEBA.xlsx')
    for col in df.columns:
        print(f"COLUMN: {col}")
except Exception as e:
    print(e)
