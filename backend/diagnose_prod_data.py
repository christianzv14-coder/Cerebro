import requests
import sys
import json

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

ACCOUNTS = [
    {"email": "admin@cerebro.com", "pass": "123456"},
    {"email": "pedro@cerebro.com", "pass": "123456"},
    {"email": "juan.perez@cerebro.com", "pass": "123456"}
]

def detailed_diag():
    print(f"--- DETAILED DIAGNOSTIC FOR ALL USERS ---")
    
    for acc in ACCOUNTS:
        print(f"\n[Testing User]: {acc['email']}")
        try:
            # Login
            res = requests.post(f"{BASE_URL}/auth/login", data={"username": acc['email'], "password": acc['pass']})
            if res.status_code != 200:
                print(f"   LOGIN FAILED: {res.status_code}")
                continue
                
            token = res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Identity
            me = requests.get(f"{BASE_URL}/users/me", headers=headers).json()
            print(f"   Identity: '{me.get('tecnico_nombre')}'")
            
            # Activities
            act_res = requests.get(f"{BASE_URL}/activities/", headers=headers)
            if act_res.status_code == 200:
                acts = act_res.json()
                print(f"   ACTIVITIES: {len(acts)}")
                for a in acts:
                     print(f"      -> ID:{a['ticket_id']} | Date:{a['fecha']} | Tech:{a['tecnico_nombre']}")
            else:
                print(f"   Activities Error: {act_res.status_code}")
                
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    detailed_diag()
