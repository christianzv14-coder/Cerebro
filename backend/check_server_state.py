
import requests
BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

print(f"--- CHECKING SERVER DEBUG STATE ---")
try:
    # No auth needed for this temp endpoint as I removed Depends(current_user) in my thought process? 
    # Let's check what I wrote.
    # "@router.get("/debug_state") ... def get_debug_state(db: Session = Depends(get_db))"
    # Yes, no user dependency. Public endpoint (for now).
    
    resp = requests.get(f"{BASE_URL}/admin/debug_state")
    if resp.status_code == 200:
        data = resp.json()
        print(f"DATE: {data['date']}")
        
        active = data['active_techs_in_plan']
        signed = data['signed_techs_in_db']
        pending = data['pending_techs']
        
        print(f"ACTIVE COUNT: {len(active)} -> {active}")
        print(f"SIGNED COUNT: {len(signed)} -> {signed}")
        print(f"PENDING COUNT: {len(pending)} -> {pending}")
        
        if not pending:
            print(">>> ALL CLEAR. EMAIL SHOULD HAVE BEEN SENT.")
        else:
            print(">>> BLOCKED. WAITING FOR PENDING.")
            
    else:
        print(f"ERROR: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"CRASH: {e}")
