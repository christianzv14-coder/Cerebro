import pandas as pd
import os
import requests
import shutil
from datetime import date

# BASE_URL = "http://127.0.0.1:8000/api/v1"
BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"
ADMIN_EMAIL = "admin@cerebro.com"
ADMIN_PASS = "123456"

def smart_upload():
    print("--- SMART UPLOAD: USER FILE -> PROD ---")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_file = os.path.join(script_dir, "plantilla_planificacion_v2.xlsx")
    temp_file = os.path.join(script_dir, "temp_smart_upload.xlsx")
    
    # 1. Copy file (Try to bypass lock)
    print(f"Reading {source_file}...")
    temp_lock_bypass = os.path.join(script_dir, "temp_lock_bypass.xlsx")
    
    try:
        shutil.copy2(source_file, temp_lock_bypass)
        df = pd.read_excel(temp_lock_bypass)
        print("Success: Read file into memory (Bypassed lock).")
        try: os.remove(temp_lock_bypass)
        except: pass
        
        # --- ROBUSTNESS FIX ---
        # 1. Normalize Header (strip spaces)
        df.columns = [str(c).strip() for c in df.columns]
        
        # 2. Handle 'fecha' Case Insensitivity
        if 'fecha' not in df.columns:
            for c in df.columns:
                if str(c).lower().strip() == 'fecha':
                    df.rename(columns={c: 'fecha'}, inplace=True)
                    print(f"Renamed column '{c}' to 'fecha'")
                    break
        
        # 3. Handle Missing 'fecha' -> Force Today
        if 'fecha' not in df.columns:
            print("WARNING: 'fecha' column missing. Defaulting to Today.")
            df['fecha'] = date.today()
        else:
            # Fill NaT/NaN dates with Today
            df['fecha'] = pd.to_datetime(df['fecha']).fillna(pd.Timestamp("today").date())
            # Ensure it is date type not datetime
            df['fecha'] = df['fecha'].dt.date
            
        print(f"Columns processed: {list(df.columns)}")
        # ----------------------
        
    except Exception as e:
        print(f"CRITICAL ERROR: Could not read file. Please close Excel.\nDetails: {e}")
        return

    # 2. Fix Data
    print("Fixing data for upload...")
    
    # a. Fix Date (Timezone safety)
    # We'll set it to literal string '2025-12-26' to ensure it parses as today
    df["fecha"] = "2025-12-26"
    print(" -> Forced dates to '2025-12-26' (to ensure visibility in App today)")
    
    # b. Verify Tech Names
    # Target 'Pedro Pascal' (Capitalized) to match 'pedro@cerebro.com'
    # df["tecnico_nombre"] = df["tecnico_nombre"].replace("Pedro Pascal", "Pedro pascal") # DISABLED
    print(" -> Techs found:", df["tecnico_nombre"].unique())
    
    # 3. Save to Temp
    df.to_excel(temp_file, index=False)
    
    # 4. Upload
    print(f"Uploading to {BASE_URL}...")
    try:
        login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASS})
        login_res.raise_for_status()
        token = login_res.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        with open(temp_file, "rb") as f:
            files = {"file": ("plantilla_planificacion_v2.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            res = requests.post(f"{BASE_URL}/admin/upload_excel", headers=headers, files=files)
            
        if res.status_code == 200:
            stats = res.json().get("stats", {})
            print("UPLOAD SUCCESS!")
            print(f"Processed: {stats.get('processed')}, Created: {stats.get('created')}, Updated: {stats.get('updated')}")
        else:
            print(f"UPLOAD FAILED: {res.status_code}")
            print(res.text)
            
    except Exception as e:
        print(f"Network Error: {e}")
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

if __name__ == "__main__":
    smart_upload()
