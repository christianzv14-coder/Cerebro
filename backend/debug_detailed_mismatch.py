import requests
import json
import sys

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"
USERS = [
    {"email": "juan.perez@cerebro.com", "pass": "123456"},
    {"email": "pedro.pascal@cerebro.com", "pass": "123456"}
]

def debug_mismatch():
    print(f"--- DEEP INSPECTION: {BASE_URL} ---")
    
    for u in USERS:
        print(f"\n[USER] {u['email']}")
        try:
            # Login
            res = requests.post(f"{BASE_URL}/auth/login", data={"username": u['email'], "password": u['pass']})
            if res.status_code != 200:
                print(f"   LOGIN FAIL: {res.status_code}")
                continue
            
            token = res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Identity
            me = requests.get(f"{BASE_URL}/users/me", headers=headers).json()
            user_name = me['tecnico_nombre']
            print(f"   Identity Name: '{user_name}'")
            print(f"   Hex Dump:      {':'.join('{:02x}'.format(ord(c)) for c in user_name)}")
            
            # Activities (No Date Filter -> Get All)
            act_res = requests.get(f"{BASE_URL}/activities/", headers=headers)
            if act_res.status_code == 200:
                acts = act_res.json()
                print(f"   Activities Found: {len(acts)}")
                for i, a in enumerate(acts):
                    t_name = a['tecnico_nombre']
                    date_val = a['fecha']
                    print(f"      [{i}] Ticket: {a['ticket_id']}")
                    print(f"          Tech Name: '{t_name}'")
                    print(f"          Hex Dump:  {':'.join('{:02x}'.format(ord(c)) for c in t_name)}")
                    print(f"          Date:      '{date_val}' (Type: {type(date_val)})")
                    
                    # Check Match
                    if t_name == user_name:
                         print("          MATCH: YES")
                    else:
                         print("          MATCH: NO  <-- PROBLEM HERE?")
            else:
                print(f"   FETCH FAIL: {act_res.status_code}")
                
        except Exception as e:
            print(f"   ERROR: {e}")

if __name__ == "__main__":
    debug_mismatch()
