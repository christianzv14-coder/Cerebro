import requests
import json
import sys

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"
USERS = [
    {"email": "juan.perez@cerebro.com", "pass": "123456"}
]

def check_sig():
    print(f"--- CHECK SIGNATURE ENDPOINT: {BASE_URL}/signatures/status ---")
    
    for u in USERS:
        print(f"\n[USER] {u['email']}")
        try:
            # Login
            res = requests.post(f"{BASE_URL}/auth/login", data={"username": u['email'], "password": u['pass']})
            if res.status_code != 200:
                print(f"   LOGIN FAIL: {res.status_code}")
                continue
            
            token = res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Call Signature Status
            sig_url = f"{BASE_URL}/signatures/status"
            print(f"   Calling {sig_url}...")
            sig_res = requests.get(sig_url, headers=headers)
            
            print(f"   Status Code: {sig_res.status_code}")
            print(f"   Body: {sig_res.text}")
            
            if sig_res.status_code == 200:
                print("   [PASS] Endpoint exists.")
            else:
                 print("   [FAIL] Endpoint error.")
                
        except Exception as e:
            print(f"   ERROR: {e}")

if __name__ == "__main__":
    check_sig()
