import requests
import json
from datetime import date, timedelta

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"
USER = {"email": "juan.perez@cerebro.com", "pass": "123456"}

def verify_flex():
    print(f"--- CHECK FLEXIBLE DATE: {BASE_URL} ---")
    
    # 1. Login
    res = requests.post(f"{BASE_URL}/auth/login", data={"username": USER['email'], "password": USER['pass']})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Get Today
    today = date.today()
    print(f"Server Today: {today}")
    
    # 3. Query TOMORROW (Simulating user asking for wrong date)
    tomorrow = today + timedelta(days=1)
    
    url = f"{BASE_URL}/activities/?fecha={tomorrow}"
    print(f"Querying for TOMORROW: {url}")
    
    act_res = requests.get(url, headers=headers)
    acts = act_res.json()
    
    print(f"Activities Found: {len(acts)}")
    if len(acts) > 0:
        print("   [PASS] Flexible Date Fix IS ACTIVE. (Found activities despite seeking tomorrow)")
    else:
        print("   [FAIL] Flexible Date Fix IS NOT ACTIVE. (Returned 0)")

if __name__ == "__main__":
    verify_flex()
