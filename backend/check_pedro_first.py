import requests
import datetime

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

def check_pedro_first():
    print("--- CHECKING PEDRO FIRST ---")
    users = [
        {"email": "pedro.pascal@cerebro.com", "pass": "123456", "name": "Pedro Pascal"},
        {"email": "juan.perez@cerebro.com", "pass": "123456", "name": "Juan Perez"}
    ]
    
    for u in users:
        print(f"\nChecking {u['name']} ({u['email']})...")
        try:
            # Login
            res = requests.post(f"{BASE_URL}/auth/login", data={"username": u['email'], "password": u['pass']})
            token = res.json().get("access_token")
            if not token:
                print("  LOGIN FAIL")
                continue
                
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get Tasks
            acts = requests.get(f"{BASE_URL}/activities/", headers=headers).json()
            print(f"  Result: {len(acts)} activities found.")
            for a in acts:
                print(f"    - Ticket: {a['ticket_id']} | Date: {a['fecha']} | Tech: {a['tecnico_nombre']}")
                
        except Exception as e:
            print(f"  Result: ERROR {e}")

if __name__ == "__main__":
    check_pedro_first()
