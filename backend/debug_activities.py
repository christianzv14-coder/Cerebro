import requests
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def debug_api():
    print(f"--- DEBUGGING ACTIVITY JSON ---")
    
    # 1. Login
    login_url = f"{BASE_URL}/auth/login"
    try:
        resp = requests.post(login_url, data={'username': 'juan.perez@cerebro.com', 'password': '123456'})
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            return
        token = resp.json()['access_token']
        print("Login SUCCESS. Token acquired.")
    except Exception as e:
        print(f"Login connection error: {e}")
        return

    # 2. Get Activities
    headers = {'Authorization': f'Bearer {token}'}
    try:
        # Fetching today's activities implicitly
        resp = requests.get(f"{BASE_URL}/activities/", headers=headers)
        print(f"GET Activities Status: {resp.status_code}")
        
        data = resp.json()
        print("\n--- RAW JSON DATA ---")
        import json
        print(json.dumps(data, indent=2))
        
        print("\n--- NULL CHECK ---")
        for i, act in enumerate(data):
            print(f"Activity {i} ({act.get('ticket_id')}):")
            print(f"  - hora_inicio: {act.get('hora_inicio')} (Type: {type(act.get('hora_inicio'))})")
            print(f"  - hora_fin: {act.get('hora_fin')} (Type: {type(act.get('hora_fin'))})")
            print(f"  - patente: {act.get('patente')} (Type: {type(act.get('patente'))})")
            print(f"  - estado: {act.get('estado')}")
            
    except Exception as e:
        print(f"Fetch failed: {e}")

if __name__ == "__main__":
    debug_api()
