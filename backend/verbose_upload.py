import pandas as pd
import os
import requests
import shutil

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"
ADMIN_EMAIL = "admin@cerebro.com"
ADMIN_PASS = "123456"

def verbose_upload():
    print("--- VERBOSE UPLOAD DIAGNOSTIC ---")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_file = os.path.join(script_dir, "plantilla_planificacion_v2.xlsx")
    
    # 1. READ EXCEL
    print(f"1. Reading {source_file}...")
    temp_lock_bypass = os.path.join(script_dir, "temp_lock_bypass_verbose.xlsx")
    
    try:
        shutil.copy2(source_file, temp_lock_bypass)
        df = pd.read_excel(temp_lock_bypass)
        print("   -> Success (Bypassed lock)")
        try: os.remove(temp_lock_bypass)
        except: pass
    except Exception as e:
        print(f"   -> FAIL: {e}")
        return

    # 2. PRINT CONTENT (SAFE MODE)
    print("\n2. EXCEL COLUMNS:")
    print(f"   Columns found: {list(df.columns)}")
    
    # Normalize if needed?
    # df.columns = [c.strip().lower() for c in df.columns]
    
    if "fecha" not in df.columns:
        print("   [CRITICAL] 'fecha' column missing! Verify headers.")
        # Try finding it case-insensitive
        for c in df.columns:
            if str(c).lower().strip() == "fecha":
                print(f"   (Found '{c}' which might mean 'fecha', renaming...)")
                df.rename(columns={c: "fecha"}, inplace=True)

    if "tecnico_nombre" not in df.columns:
         print("   [CRITICAL] 'tecnico_nombre' missing!")
         
    # Now try to print
    if "tecnico_nombre" in df.columns:
        print("   --- TASKS PER TECH ---")
        try:
            print(df["tecnico_nombre"].value_counts())
        except:
            print("   (Could not count techs)")

        print("   --- PEDRO PASCAL TASKS ---")
        try:
            pedro_df = df[df["tecnico_nombre"].isin(["Pedro Pascal", "Pedro pascal"])]
            if not pedro_df.empty:
                for i, row in pedro_df.iterrows():
                     d_val = row.get('fecha', 'N/A')
                     t_val = row.get('ticket_id', 'N/A')
                     print(f"   Row {i+2}: Ticket {t_val} | Date: {d_val}")
            else:
                print("   (No tasks found for Pedro Pascal)")
        except Exception as e:
            print(f"Error printing rows: {e}")
    else:
        print("   [ERR] Column 'tecnico_nombre' missing!")

    # 3. UPLOAD?
    confirm = input("\nDo these look correct? (Uploaded automatically for user simulation) [Y/n] ")
    # Simulation: We assume yes and upload to check server response
    
    print("\n3. UPLOADING TO SERVER...")
    try:
        # Save temp for upload
        temp_up = os.path.join(script_dir, "temp_verbose_up.xlsx")
        df.to_excel(temp_up, index=False)
        
        login = requests.post(f"{BASE_URL}/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASS})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        with open(temp_up, "rb") as f:
            files = {"file": ("plantilla_planificacion_v2.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            res = requests.post(f"{BASE_URL}/admin/upload_excel", headers=headers, files=files)
            
        if res.status_code == 200:
            print("   -> UPLOAD SUCCESS")
            print(f"   Stats: {res.json()}")
        else:
            print(f"   -> UPLOAD FAIL: {res.text}")
            
    except Exception as e:
        print(f"   -> Network Error: {e}")
    finally:
        if os.path.exists(temp_up): os.remove(temp_up)

if __name__ == "__main__":
    verbose_upload()
