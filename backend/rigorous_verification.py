import requests
import json
from datetime import date, datetime

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"
# DATE_TO_CHECK = "2025-12-26"
DATE_TO_CHECK = str(date.today()) 

USERS = [
    {"email": "juan.perez@cerebro.com", "pass": "123456", "role": "TECH"},
    {"email": "pedro.pascal@cerebro.com", "pass": "123456", "role": "TECH"}
]

def verify_rigorous():
    print(f"=== RIGOROUS VERIFICATION SUITE ===")
    print(f"Target: {BASE_URL}")
    print(f"Date to check: {DATE_TO_CHECK}")
    
    print("\n[PART 1: DATA EXISTENCE & APP VISIBILITY]")
    
    for u in USERS:
        print(f"\n--- Testing User: {u['email']} ---")
        try:
            # 1. Login
            params = {"username": u['email'], "password": u['pass']}
            res = requests.post(f"{BASE_URL}/auth/login", data=params)
            
            if res.status_code != 200:
                print(f"   [FAIL] Login Error: {res.status_code} {res.text}")
                continue
                
            token = res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("   [PASS] Login Successful")
            
            # 2. Get User Profile
            me = requests.get(f"{BASE_URL}/users/me", headers=headers).json()
            print(f"   [PASS] Identity: {me['tecnico_nombre']} (ID: {me['id']})")
            
            # 3. Simulate App Request (Filtered by Date)
            # The App calls: /activities/?fecha=YYYY-MM-DD
            app_url = f"{BASE_URL}/activities/?fecha={DATE_TO_CHECK}"
            print(f"   [TEST] Calling App Endpoint: {app_url}")
            
            act_res = requests.get(app_url, headers=headers)
            
            if act_res.status_code == 200:
                data = act_res.json()
                print(f"   [RESULT] Activities Found: {len(data)}")
                if len(data) == 0:
                    print(f"   [WARNING] App sees 0 activities for today.")
                    # Try fetching ALL to see if dates are wrong
                    all_url = f"{BASE_URL}/activities/"
                    print(f"   [DEBUG] Fetching ALL activities (no date filter)...")
                    all_res = requests.get(all_url, headers=headers).json()
                    print(f"   [DEBUG] Total Activities for user: {len(all_res)}")
                    for a in all_res:
                         print(f"      -> ID: {a['ticket_id']} | Date: {a['fecha']} | State: {a['estado']}")
                else:
                    for a in data:
                        print(f"      -> [OK] ID: {a['ticket_id']} | State: {a['estado']} | {a['tipo_trabajo']}")
            else:
                print(f"   [FAIL] API Error: {act_res.status_code}")
                
        except Exception as e:
            print(f"   [FATAL] Script error: {e}")

    print("\n[PART 2: GOOGLE SHEETS SYNC TEST]")
    # We will try to update one activity for the last user to trigger a sheet sync
    if 'token' in locals():
        try:
            # Find a PENDING activity
            if 'data' in locals() and len(data) > 0:
                target_act = data[0]
                tid = target_act['ticket_id']
                print(f"--- Testing Sheets Sync on Ticket {tid} ---")
                
                # We'll just "Start" it. This triggers Sheet UPDATE (Inicio).
                start_url = f"{BASE_URL}/activities/{tid}/start"
                print(f"   [ACTION] calling {start_url} ...")
                
                start_res = requests.post(
                    start_url, 
                    headers=headers, # reuse last token
                    json={"timestamp": datetime.now().isoformat()}
                )
                
                if start_res.status_code == 200:
                    print("   [PASS] Activity Started in DB.")
                    print("   [CHECK] Check your Google Sheet. Did 'Inicio' column update for this ticket?")
                else:
                    print(f"   [FAIL] Activity Start Failed: {start_res.status_code} {start_res.text}")
            else:
                print("   [SKIP] No activities available to test sync.")
        except Exception as e:
             print(f"   [ERROR] Sync test error: {e}")

if __name__ == "__main__":
    verify_rigorous()
