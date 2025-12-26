import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/api/v1"

def debug_start():
    print("--- DEBUGGING START ACTIVITY ---")
    
    # 1. Login
    login_url = f"{BASE_URL}/auth/login"
    try:
        resp = requests.post(login_url, data={'username': 'juan.perez@cerebro.com', 'password': '123456'})
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            return
        token = resp.json()['access_token']
        print("Login SUCCESS.")
    except Exception as e:
        print(f"Login connection error: {e}")
        return

    # 2. Start Activity
    # Assuming TKT-MAÑ-01 based on screenshots, or fetch first pending.
    headers = {'Authorization': f'Bearer {token}'}
    
    # First get list to find a ticket
    try:
        list_resp = requests.get(f"{BASE_URL}/activities/", headers=headers)
        activities = list_resp.json()
        target = None
        for a in activities:
            if a['estado'] == 'PENDIENTE':
                target = a
                break
        
        if not target:
            print("No PENDIENTE activities found to start.")
            return

        ticket_id = target['ticket_id']
        print(f"Attempting to START {ticket_id}...")
        
        start_url = f"{BASE_URL}/activities/{ticket_id}/start"
        payload = {'timestamp': datetime.utcnow().isoformat()}
        
        start_resp = requests.post(start_url, json=payload, headers=headers)
        
        print(f"START Response Code: {start_resp.status_code}")
        print(f"START Body: {start_resp.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_start()
