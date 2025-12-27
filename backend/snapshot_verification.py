import requests

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

ACCOUNTS = [
    {"email": "juan.perez@cerebro.com", "pass": "123456"},
    {"email": "pedro.pascal@cerebro.com", "pass": "123456"},
    {"email": "pedro@cerebro.com", "pass": "123456"}
]

def snapshot():
    print("--- SNAPSHOT ---")
    
    # 1. Dump Users
    print("\n[USERS]")
    for acc in ACCOUNTS:
        try:
            res = requests.post(f"{BASE_URL}/auth/login", data={"username": acc['email'], "password": acc['pass']})
            if res.status_code == 200:
                token = res.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                me = requests.get(f"{BASE_URL}/users/me", headers=headers).json()
                print(f"Email: {acc['email']} | Name: '{me['tecnico_nombre']}'")
            else:
                print(f"Email: {acc['email']} | LOGIN FAIL")
        except Exception as e:
            print(f"Email: {acc['email']} | ERR: {e}")

    # 2. Dump Activities
    print("\n[ACTIVITIES (Raw)]")
    # Use Juan's token (assuming he has some access, or Admin if needed)
    # Admin is best
    try:
        res = requests.post(f"{BASE_URL}/auth/login", data={"username": "admin@cerebro.com", "password": "123456"})
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        acts = requests.get(f"{BASE_URL}/activities/", headers=headers).json()
        print(f"Total: {len(acts)}")
        for a in acts:
            print(f"Ticket: {a['ticket_id']} | Tech: '{a['tecnico_nombre']}' | Date: {a['fecha']}")
            
    except Exception as e:
        print(f"Activity Dump FAiled: {e}")

if __name__ == "__main__":
    snapshot()
