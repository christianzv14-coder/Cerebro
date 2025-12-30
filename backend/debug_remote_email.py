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
        # print(f"ROOT BODY: {root_resp.text[:100]}")

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
        
        # 2. Trigger Debug Email
        print("2. Triggering Debug Email...")
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/users/debug/email", headers=headers)
        
        print(f"RESPONSE STATUS: {resp.status_code}")
        print(f"RESPONSE BODY: {resp.text}")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_email()
