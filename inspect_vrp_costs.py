
import pandas as pd

def inspect_costs():
    fpath = "outputs/plan_logistico_optimizado.xlsx"
    print(f"Reading: {fpath}")
    
    df = pd.read_excel(fpath)
    
    # Sum Columns
    total_travel = df['Travel ($)'].sum()
    total_viatico = df['Viatico ($)'].sum()
    total_lodging = df['Lodging ($)'].sum()
    total_project = df['Total ($)'].sum()
    
    print("\n--- COST BREAKDOWN ---")
    print(f"Travel (Bencina/Peaje): ${total_travel:,.0f}")
    print(f"Viatico (Comida):       ${total_viatico:,.0f}")
    print(f"Lodging (Hotel):        ${total_lodging:,.0f}")
    print(f"---------------------------")
    print(f"TOTAL:                  ${total_project:,.0f}")
    
    # Calculate Percentages
    print("\n--- PERCENTAGES ---")
    print(f"Travel:  {(total_travel/total_project)*100:.1f}%")
    print(f"Viatico: {(total_viatico/total_project)*100:.1f}%")
    print(f"Lodging: {(total_lodging/total_project)*100:.1f}%")

if __name__ == "__main__":
    inspect_costs()
