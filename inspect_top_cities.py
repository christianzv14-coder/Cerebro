import pandas as pd
df = pd.read_excel('outputs/plan_enex_detalle_granular.xlsx')
top5 = df.groupby('Destino')['Total'].sum().sort_values(ascending=False).head(5)
print("--- TOP 5 CIUDADES MÁS CARAS ---")
for city, cost in top5.items():
    print(f"{city}: ${int(cost):,}")
