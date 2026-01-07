import requests
import sys

BASE_URL = "https://pacific-determination-production.up.railway.app/api/v1"

def test_login_loop():
    session = requests.Session()
    
    # 1. Login
    print(">>> Attempting Login...")
    try:
        resp = session.post(f"{BASE_URL}/auth/login", data={"username": "christian.zv@cerebro.com", "password": "123456"})
    except Exception as e:
        print(f"Login Network Fail: {e}")
        return

    if resp.status_code != 200:
        print(f"Login FAILED: {resp.status_code} - {resp.text}")
        return
    
    data = resp.json()
    token = data.get("access_token")
    if not token:
        print("Login SUCCESS but NO TOKEN returned!")
        return
    
    print(f"Login SUCCESS. Token received (len={len(token)})")

    # 2. Simulate refreshData() -> loadDashboard()
    print(">>> simulating refreshData() calls...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Call dashboard
    resp = session.get(f"{BASE_URL}/expenses/dashboard", headers=headers)
    print(f"GET /dashboard Status: {resp.status_code}")
    if resp.status_code == 401:
        print("CRITICAL: Dashboard returned 401 immediately after login! This causes the loop.")
        print(f"Body: {resp.text}")
    elif resp.status_code == 200:
        print("Dashboard OK.")
    else:
        print(f"Dashboard returned {resp.status_code}")

    # Call expenses
    resp = session.get(f"{BASE_URL}/expenses/", headers=headers)
    print(f"GET /expenses/ Status: {resp.status_code}")
    if resp.status_code == 401:
        print("CRITICAL: Expenses returned 401 immediately after login!")

if __name__ == "__main__":
    test_login_loop()
