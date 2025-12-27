import requests
import datetime

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

def check_prod_tasks():
    print("--- CHECKING PROD TASKS ---")
    users = [
        {"email": "juan.perez@cerebro.com", "pass": "123456", "name": "Juan Perez"},
        {"email": "pedro.pascal@cerebro.com", "pass": "123456", "name": "Pedro Pascal"}
    ]
    
    for u in users:
        print(f"\nChecking {u['name']} ({u['email']})...")
        try:
            # Login
            res = requests.post(f"{BASE_URL}/auth/login", data={"username": u['email'], "password": u['pass']})
            if res.status_code != 200:
                print(f"  Result: LOGIN FAILED ({res.status_code})")
                continue
                
            token = res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get Tasks
            acts = requests.get(f"{BASE_URL}/activities/", headers=headers).json()
            print(f"  Result: {len(acts)} activities found.")
            for a in acts:
                print(f"    - Ticket: {a['ticket_id']} | Date: {a['fecha']} | State: {a['estado']}")
                
        except Exception as e:
            print(f"  Result: ERROR {e}")

if __name__ == "__main__":
    check_prod_tasks()
