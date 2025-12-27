import requests
import sys

# BASE_URL = "http://127.0.0.1:8000/api/v1"
BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

ADMIN_EMAIL = "admin@cerebro.com"
ADMIN_PASS = "123456"

def test_connection():
    print(f"--- TRACE: Testing Connection to {BASE_URL} ---")
    
    # 1. Health/Root Check (Optional, but good sanity check if root endpoint exists, otherwise just try login)
    
    # 2. Login
    print(f"1. Attempting Login as {ADMIN_EMAIL}...")
    try:
        login_res = requests.post(f"{BASE_URL}/auth/login", data={
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASS
        })
        
        if login_res.status_code != 200:
            print(f"   [FAIL] Login Failed: {login_res.status_code}")
            print(f"   Response: {login_res.text}")
            print("   -> CAUSE: Likely the Railway DB is empty. You need to run 'init_data.py' or seeded data.")
            return
            
        token = login_res.json()["access_token"]
        print("   [SUCCESS] Login OK. Token received.")
        
    except Exception as e:
        print(f"   [ERROR] Connection refused or network error: {e}")
        return

    # 3. Fetch Activities
    print("2. Fetching Activities...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # Get all activities (ticket_id, tecnico_nombre, fecha)
        # Note: The endpoint usually filters by current user or date? 
        # The admin/upload endpoint might be different, but let's try standard get.
        # But 'admin' user might not have activities assigned.
        # Let's try to get 'users/me' to confirm who we are.
        
        me_res = requests.get(f"{BASE_URL}/users/me", headers=headers)
        if me_res.status_code == 200:
            user_data = me_res.json()
            print(f"   [INFO] Logged in as: {user_data.get('tecnico_nombre')} (Role: {user_data.get('role')})")
        
        # Checking activities for 'Juan Perez' (common test user) or just any if possible
        # Actually, let's just inspect what the upload endpoint would return/do? No, upload is POST.
        # Inspecting standard activities endpoint.
        activities_res = requests.get(f"{BASE_URL}/activities/", headers=headers)
        
        if activities_res.status_code == 200:
            activities = activities_res.json()
            print(f"   [INFO] Found {len(activities)} activities for this user.")
            if len(activities) == 0:
                print("   -> WARNING: Activity list is EMPTY.")
            else:
                for a in activities:
                    print(f"      - {a.get('ticket_id')} | {a.get('tecnico_nombre')} | {a.get('fecha')} | {a.get('estado')}")
        else:
            print(f"   [FAIL] Fetch Activities failed: {activities_res.status_code}")

    except Exception as e:
        print(f"   [ERROR] {e}")

if __name__ == "__main__":
    test_connection()
