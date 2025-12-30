
import requests
BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

print(f"--- CHECKING SERVER ENV VARS ---")
try:
    # Need auth for debug_full_system? 
    # View file said: `def debug_full_system(db: Session = Depends(get_db)):`
    # No user dependency!
    resp = requests.get(f"{BASE_URL}/admin/debug_full_system")
    if resp.status_code == 200:
        data = resp.json()
        print(f"ENV VARS: {data['env_vars']}")
    else:
        print(f"ERROR: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"CRASH: {e}")
