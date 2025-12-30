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
URL = f"{BASE_URL}/api/v1/admin/debug_score_sync"

try:
    print(f"Calling Debug Endpoint: {URL}")
    resp = requests.get(URL, timeout=60) # High timeout for sheet read
    
    if resp.status_code == 200:
        data = resp.json()
        print("\n>>> REMOTE LOGS START <<<")
        for line in data.get("logs", []):
            print(line)
        print(">>> REMOTE LOGS END <<<")
    else:
        print(f"Error: {resp.status_code} - {resp.text}")

except Exception as e:
    print(f"Exception: {e}")
