
import requests
import json

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

def check_system():
    print(f"--- DIAGNOSING SYSTEM ({BASE_URL}) ---")
    
    # 1. Login (as User) to check 'status'
    login_data = {"username": "juan.perez@cerebro.com", "password": "123456"}
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            print("-> Login OK (Juan Perez)")
            
            # Check Signature Status
            # Need a date? Defaults to today.
            resp_sig = requests.get(f"{BASE_URL}/signatures/status", headers=headers)
            print(f"-> SIGNATURE STATUS: {resp_sig.json()}")
        else:
            print(f"-> Login FAILED: {resp.status_code}")
    except Exception as e:
        print(f"-> Login Exception: {e}")

    # 2. Test Email Capability (Public Admin Endpoint)
    print("\n--- TESTING EMAIL SENDING CAPABILITY ---")
    try:
        resp = requests.get(f"{BASE_URL}/admin/test_email")
        print(f"-> TEST EMAIL ENDPOINT STATUS: {resp.status_code}")
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)
    except Exception as e:
        print(f"-> Test Email Exception: {e}")

if __name__ == "__main__":
    check_system()
