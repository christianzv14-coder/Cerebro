
import requests
import sys

# BASE_URL = "http://127.0.0.1:8001/api/v1" 
BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

def test_prod_email():
    print(f"Testing Email Config on: {BASE_URL}")
    try:
        # Try without auth first (based on code inspection)
        res = requests.get(f"{BASE_URL}/admin/test_email")
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            print("Response:", res.json())
        elif res.status_code == 401:
            print("Auth required. Logging in...")
            # Login flow
            login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": "admin@cerebro.com", "password": "123456"})
            if login_res.status_code == 200:
                token = login_res.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                res = requests.get(f"{BASE_URL}/admin/test_email", headers=headers)
                print(f"Status with Auth: {res.status_code}")
                print("Response:", res.json())
            else:
                print("Login Failed")
        else:
            print(f"Error: {res.text}")
            
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    test_prod_email()
