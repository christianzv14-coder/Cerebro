import requests
import os
import sys

# Change this to your Railway URL if needed, or localhost if port forwarding
# But here we want to debug the REMOTE.
BASE_URL = "https://cerebro-production-89cc.up.railway.app" 
# Assuming this is the URL. I should check if I have it in previous context, 
# otherwise I might need to ask or use the one I used for verify_resend.
# Previous logs showed: "Checking health at https://cerebro-production-89cc.up.railway.app"

# Endpoint
URL = f"{BASE_URL}/debug_score_sync_direct"

try:
    print(f"--- DIAGNOSTICS ---")
    
    # 1. Check Root
    try:
        r = requests.get(BASE_URL + "/", timeout=5)
        print(f"ROOT (/): {r.status_code} - {r.text[:100]}")
    except Exception as e:
        print(f"ROOT (/): FAILED - {e}")

    # 2. Check Signatures Ping
    try:
        r = requests.get(BASE_URL + "/api/v1/signatures/ping", timeout=5)
        print(f"SIG PING: {r.status_code} - {r.text[:100]}")
    except Exception as e:
        print(f"SIG PING: FAILED - {e}")

    # 3. Check Admin Endpoint
    print(f"Calling Debug Endpoint: {URL}")
    resp = requests.post(URL) # Wait, getting it as POST? No, I defined GET.
    # Check definition in admin.py: @router.get("/debug_score_sync")
    # Wait! In Step 1902 replacement, I see:
    # @router.post("/debug_resend") ...
    # @router.get("/debug_score_sync") ...
    # So it is GET.
    
    resp = requests.get(URL, timeout=60)
    
    if resp.status_code == 200:
        data = resp.json()
        print("\n>>> REMOTE LOGS START <<<")
        for line in data.get("logs", []):
            print(line)
        print(">>> REMOTE LOGS END <<<")
    else:
        print(f"Target Endpoint Error: {resp.status_code} - {resp.text}")

except Exception as e:
    print(f"Exception: {e}")
