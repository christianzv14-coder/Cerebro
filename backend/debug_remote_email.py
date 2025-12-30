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
        
        # 2. TRIGGER RESET (NUCLEAR OPTION)
        print("2. TRIGGERING REMOTE RESET (Delete all plans)...")
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.delete(f"{BASE_URL}/activities/reset", headers=headers)
        
        print(f"RESET STATUS: {resp.status_code}")
        print(f"RESET BODY: {resp.text}")

        # 3. Simulate Full Closure (Admin) - Optional
        # print("2. Simulating FULL CLOSURE (Auto-sign all pending)...")
        # headers = {"Authorization": f"Bearer {token}"}
        # resp = requests.post(f"{BASE_URL}/admin/simulate_closure", headers=headers)
        # print(f"SIMULATION STATUS: {resp.status_code}")
        # print(f"SIMULATION BODY: {resp.text}")


        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_email()
