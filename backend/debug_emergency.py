import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from app.core.config import settings

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"
PEDRO = {"email": "pedro.pascal@cerebro.com", "pass": "123456"}

def debug_emergency():
    print("=== EMERGENCY DIAGNOSTIC ===")
    
    # 1. API DATA CHECK
    print("\n[1. API CHECK]")
    try:
        res = requests.post(f"{BASE_URL}/auth/login", data={"username": PEDRO['email'], "password": PEDRO['pass']})
        if res.status_code == 200:
            token = res.json()["access_token"]
            print("   Login: OK")
            
            headers = {"Authorization": f"Bearer {token}"}
            # Fetch ALL (no date filter for safety)
            acts = requests.get(f"{BASE_URL}/activities/", headers=headers).json()
            print(f"   Activities Found: {len(acts)}")
            for a in acts:
                print(f"    -> Ticket: {a['ticket_id']} | Tech: {a['tecnico_nombre']}")
        else:
            print(f"   Login FAIL: {res.status_code} {res.text}")
    except Exception as e:
        print(f"   API Error: {e}")

    # 2. SHEETS CONNECTIVITY CHECK
    print("\n[2. GOOGLE SHEETS CHECK]")
    try:
        # Load creds from file or env?
        # We'll assume the file 'credentials.json' is in backend/ based on previous context, 
        # OR we try to initialize using the app's internal logic.
        # Let's try to just use gspread directly if file exists.
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Check environment var method first (Production way)
        creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
        if creds_json:
            print("   Using ENV Credentials...")
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        elif os.path.exists("credentials.json"):
             print("   Using File 'credentials.json'...")
             creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        else:
             print("   [FAIL] No credentials found (Env or File).")
             return

        client = gspread.authorize(creds)
        sheet_id = os.getenv("GOOGLE_SHEET_ID") or "1F-xxxxxxxx" # Placeholder, relying on user or .env
        # Actually, let's try to read .env file manually if needed, or rely on system env.
        # User local has .env
        
        # We need the real SHEET ID. I'll read it from .env locally.
        from dotenv import load_dotenv
        load_dotenv()
        real_sheet_id = os.getenv("GOOGLE_SHEET_ID")
        print(f"   Target Sheet ID: {real_sheet_id}")
        
        sh = client.open_by_key(real_sheet_id)
        worksheet = sh.worksheet("Bitacora") 
        print(f"   [PASS] Connected to Sheet: {sh.title} -> Bitacora")
        print(f"   Rows: {len(worksheet.get_all_values())}")
        
    except Exception as e:
        print(f"   [FAIL] Sheets Error: {e}")

if __name__ == "__main__":
    debug_emergency()
