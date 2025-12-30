
import requests
import json
import time

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

def check_resend():
    print(f"--- DIAGNOSING RESEND CONFIGURATION ({BASE_URL}) ---")
    
    # Authenticate as Admin (Juan is user, need admin? 
    # Actually checking code: debug_resend is NOT protected by Depends(get_current_admin) in the code I wrote?
    # Let me check my memory/code.
    # Code snippet: @router.get("/debug_resend") ... def debug_resend(...):
    # No dependency injection! It is public. Good for quick debug, dangerous for prod (should secure later).
    
    endpoint = f"{BASE_URL}/admin/debug_resend"
    print(f"Target: {endpoint}")
    
    try:
        resp = requests.get(endpoint, timeout=15)
        print(f"Status Code: {resp.status_code}")
        
        try:
            data = resp.json()
            print(json.dumps(data, indent=2))
        except:
            print("Raw Response:", resp.text)
            
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    check_resend()
