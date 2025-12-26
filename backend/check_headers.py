import pandas as pd

def check_headers():
    print("--- PLANTILLA ---")
    try:
        df_plan = pd.read_excel("plantilla_planificacion.xlsx")
        print(df_plan.columns.tolist())
    except Exception as e:
        print(f"Error reading plantilla: {e}")

    print("\n--- COORDINADOS (Mantis) ---")
    try:
        # Assuming Coordinados (11).xlsx is the file
        df_mantis = pd.read_excel("Coordinados (11).xlsx")
        print(df_mantis.columns.tolist())
    except Exception as e:
        print(f"Error reading mantis: {e}")

if __name__ == "__main__":
    check_headers()
