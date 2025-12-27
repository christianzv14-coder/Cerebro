import shutil
import os
import requests
import sys

# BASE_URL = "http://127.0.0.1:8000/api/v1"
BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"
ADMIN_EMAIL = "admin@cerebro.com"
ADMIN_PASS = "123456"

def subir_temp():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    original = os.path.join(script_dir, "plantilla_planificacion_v2.xlsx")
    temp = os.path.join(script_dir, "temp_upload.xlsx")
    
    # 1. Copy to temp to avoid Lock
    try:
        shutil.copy(original, temp)
        print(f"Copied to {temp}")
    except Exception as e:
        print(f"Error copying: {e}")
        return

    # 2. Upload
    print(f"--- Force Uploading {temp} ---")
    try:
        # Login
        login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASS})
        login_res.raise_for_status()
        token = login_res.json()["access_token"]
        
        # Upload
        headers = {"Authorization": f"Bearer {token}"}
        with open(temp, "rb") as f:
            files = {"file": ("plantilla_planificacion_v2.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            res = requests.post(f"{BASE_URL}/admin/upload_excel", headers=headers, files=files)
            
        if res.status_code == 200:
            print("UPLOAD SUCCESS!")
            print(res.json())
        else:
            print(f"UPLOAD FAILED: {res.status_code}")
            print(res.text)
            
    except Exception as e:
        print(f"Error transferring: {e}")
    finally:
        if os.path.exists(temp):
            try:
                os.remove(temp)
            except:
                pass

if __name__ == "__main__":
    subir_temp()
