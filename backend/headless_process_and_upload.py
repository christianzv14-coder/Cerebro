import pandas as pd
import os
import requests
import sys

# BASE_URL = "http://127.0.0.1:8000/api/v1"
BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"
ADMIN_EMAIL = "admin@cerebro.com"
ADMIN_PASS = "123456"

# MAPPING CONFIG (From process_mantis.py)
COLUMN_MAPPING = {
    "ID": "ticket_id",
    "Categoría": "tipo_trabajo",
    "Dirección Visita": "direccion",
    "Patente Móvil": "patente",
    "Cuenta Position": "cliente",
    "Prioridad": "Prioridad",
    "Accesorios": "Accesorios",
    "Comuna Visita": "Comuna", 
    "Región Visita": "Region"
}

FINAL_COLUMNS = [
    "fecha", "ticket_id", "Prioridad", "tipo_trabajo", "Accesorios", 
    "direccion", "Comuna", "Region", "tecnico_nombre", "patente", "cliente"
]

def headless_automation():
    print("--- HEADLESS AUTOMATION: MANTIS -> PROD ---")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = script_dir
    files = [f for f in os.listdir(base_dir) if f.startswith("Coordinados") and f.endswith(".xlsx")]
    
    if not files:
        print("Error: No 'Coordinados' file found.")
        return

    files.sort(key=lambda x: os.path.getmtime(os.path.join(base_dir, x)), reverse=True)
    input_file = os.path.join(base_dir, files[0])
    print(f"Using input: {input_file}")
    
    # Generate Temp Output
    output_file = os.path.join(base_dir, "temp_railway_upload.xlsx")

    try:
        df = pd.read_excel(input_file)
        
        # Transform
        df_renamed = df.rename(columns=COLUMN_MAPPING)
        # FORCE ASSIGNMENT TO PEDRO PASCAL
        df_renamed["tecnico_nombre"] = "Pedro Pascal"
        
        from datetime import date
        current_date = date.today().strftime("%Y-%m-%d")
        df_renamed["fecha"] = current_date
            
        available = df_renamed.columns.tolist()
        for col in FINAL_COLUMNS:
            if col not in available:
                df_renamed[col] = "" 
                
        final_df = df_renamed[FINAL_COLUMNS]
        final_df.to_excel(output_file, index=False)
        print(f"Generated temp file: {output_file}")
        
        # Upload
        print(f"Uploading to {BASE_URL}...")
        login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASS})
        login_res.raise_for_status()
        token = login_res.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        with open(output_file, "rb") as f:
            files = {"file": ("plantilla_planificacion_v2.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            res = requests.post(f"{BASE_URL}/admin/upload_excel", headers=headers, files=files)
            
        if res.status_code == 200:
            print("UPLOAD SUCCESS!")
            print(res.json())
        else:
            print(f"UPLOAD FAILED: {res.status_code}")
            print(res.text)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
                print("Temp file removed.")
            except:
                pass

if __name__ == "__main__":
    headless_automation()
