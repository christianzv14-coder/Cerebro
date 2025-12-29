
import requests
import json
import time

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"
ADMIN_EMAIL = "admin@cerebro.com"
ADMIN_PASS = "123456"

def run_diagnostics():
    print(f"--- RUNNING FULL SYSTEM DIAGNOSIS ON {BASE_URL} ---")
    
    # 1. Login
    try:
        print("Logging in...")
        login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASS})
        if login_res.status_code != 200:
            print(f"FATAL: Login failed. Status: {login_res.status_code}, Body: {login_res.text}")
            return
        
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login Successful.")
        
        # 2. Call Debug Endpoint
        print("Invoking /admin/debug_full_system...")
        # Retry logic because server might be restarting
        for i in range(5):
            try:
                res = requests.get(f"{BASE_URL}/admin/debug_full_system", headers=headers, timeout=20)
                if res.status_code == 200:
                    report = res.json()
                    print("\n--- DIAGNOSTIC REPORT ---")
                    print(json.dumps(report, indent=4))
                    return
                elif res.status_code == 404:
                    print(f"Attempt {i+1}: Endpoint not found (Server likely outdated). Retrying in 5s...")
                else:
                    print(f"Attempt {i+1}: Status {res.status_code}. Retrying...")
            except Exception as e:
                print(f"Attempt {i+1}: Connection Error ({e}). Server restarting?")
                
            time.sleep(5)
            
        print("FATAL: Could not reach diagnostic endpoint after retries.")

    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    run_diagnostics()
