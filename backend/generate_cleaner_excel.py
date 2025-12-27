import pandas as pd
from datetime import date, timedelta

def generate_cleaner():
    print("--- GENERATING CLEANER EXCEL ---")
    
    # Define Date Range (Covering past/future to catch strays)
    start_date = date(2025, 12, 25)
    dates = [start_date + timedelta(days=i) for i in range(5)] # 25, 26, 27, 28, 29
    
    techs = ["Juan Perez", "Pedro Pascal", "Pedro pascal"]
    
    data = []
    for d in dates:
        for t in techs:
            data.append({
                "fecha": d,
                "tecnico_nombre": t,
                "ticket_id": None, # EMPTY TICKET ID triggers delete-only
                "patente": "CLEANUP",
                "cliente": "CLEANUP",
                "direccion": "CLEANUP",
                "tipo_trabajo": "CLEANUP"
            })
            
    df = pd.DataFrame(data)
    output_file = "cleaner_excel.xlsx"
    df.to_excel(output_file, index=False)
    print(f"Created {output_file} with {len(df)} cleanup rows.")

if __name__ == "__main__":
    generate_cleaner()
