
import pandas as pd

def check_bases():
    techs = pd.read_excel("data/tecnicos_internos.xlsx")
    techs.columns = [c.strip().lower() for c in techs.columns]
    
    col_name = 'tecnico' if 'tecnico' in techs.columns else 'nombre'
    
    print("--- CURRENT BASES IN FILE ---")
    for idx, row in techs.iterrows():
        name = row[col_name]
        try:
            base = row['ciudad_base']
        except KeyError:
             base = row['ciudad origen']
        print(f"{name}: {base}")

if __name__ == "__main__":
    check_bases()
