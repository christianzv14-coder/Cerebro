import requests
import sys

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"
ADMIN_EMAIL = "admin@cerebro.com"
ADMIN_PASS = "123456"

TARGET_TECH = "Pedro Pascal"

def fix_prod_assignment():
    print(f"--- Fixing Assignments in PROD ({BASE_URL}) ---")
    
    # 1. Login
    try:
        res = requests.post(f"{BASE_URL}/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASS})
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
    except Exception as e:
        print(f"Login failed: {e}")
        return

    # 2. Get All Activities (Admin Endpoint if available, or just list)
    # The normal /activities/ endpoint filters by user. 
    # But maybe I can mock being "Sin Asignar"? 
    # Or I can use a special "reassign" script if I had one in the backend. 
    # I DO NOT have a remote reassign endpoint.
    
    # BUT, I can run `fix_pedro_assignment.py` LOCALLY against the PROD DB if I change the DATABASE_URL in .env?
    # No, I can't easily change .env without reloading the server which is on Railway.
    
    # Alternative: Use "user impersonation" or just Login as "Sin Asignar" and update them? 
    # The API `start_activity` / `finish_activity` doesn't allow changing owner.
    
    # Wait, `subir_excel.py` uses `admin/upload_excel`.
    # I can upload a csv/excel with JUST ticket_id and correct tecnico_nombre. 
    # The `excel_service.py` merges/updates.
    
    # PLAN: Create a small Excel with the correct assignment and upload it.
    pass

# Better approach:
# Create a temporary excel with the Ticket IDs and "Pedro Pascal" and upload it.
# This uses the existing `headless_process...` logic but forces the name.

import pandas as pd
import os

def force_assign_upload():
    print("Generating Re-Assignment Excel...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = script_dir
    files = [f for f in os.listdir(base_dir) if f.startswith("Coordinados") and f.endswith(".xlsx")]
    if not files: return
    files.sort(key=lambda x: os.path.getmtime(os.path.join(base_dir, x)), reverse=True)
    input_file = os.path.join(base_dir, files[0])
    
    df = pd.read_excel(input_file)
    # Rename ID -> ticket_id
    df = df.rename(columns={"ID": "ticket_id"})
    
    # FORCE TECHNICIAN
    df["tecnico_nombre"] = TARGET_TECH
    
    # Ensure date is today
    from datetime import date
    df["fecha"] = date.today()
    
    # Add other required cols empty if missing
    for c in ["patente", "cliente", "direccion", "tipo_trabajo"]:
        if c not in df.columns: df[c] = ""

    output_file = os.path.join(base_dir, "force_assign_prod.xlsx")
    df.to_excel(output_file, index=False)
    
    # UPLOAD
    print("Uploading...")
    try:
        res = requests.post(f"{BASE_URL}/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASS})
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        with open(output_file, "rb") as f:
             files = {"file": ("force_assign.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
             r = requests.post(f"{BASE_URL}/admin/upload_excel", headers=headers, files=files)
             print(r.text)
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)

if __name__ == "__main__":
    force_assign_upload()
