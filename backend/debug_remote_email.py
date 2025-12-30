import requests
import sys

# Railway URL
BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

def test_email():
    print(f"--- TESTING REMOTE EMAIL ({BASE_URL}) ---")
    
    # 1. Login to get Token
    login_data = {
        "username": "juan.perez@cerebro.com",
        "password": "123456"
    }
    
    try:
        # Check Root
        print("0. Checking Root...")
        root_resp = requests.get("https://cozy-smile-production.up.railway.app/")
        print(f"ROOT STATUS: {root_resp.status_code}")

        print("1. Logging in...")
        resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        
        if resp.status_code != 200:
            print(f"LOGIN FAILED: {resp.status_code} - {resp.text}")
            return
            
        token = resp.json().get("access_token")
        if not token:
            print("LOGIN FAILED: No token returned.")
            return
            
        print(" -> Login Successful.")
        
        # 2. Check Signature Status
        print("2. Checking Signature Status for Today...")
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/signatures/status", headers=headers)
        
        print(f"SIG STATUS: {resp.status_code}")
        print(f"SIG BODY: {resp.text}")

        # 3. Trigger Debug Email (Optional, can re-enable)
        # print("3. Triggering Debug Email...")
        # resp = requests.get(f"{BASE_URL}/users/debug/email", headers=headers)
        # print(f"EMAIL STATUS: {resp.status_code}")

        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_email()
