import os
import json
from dotenv import load_dotenv

def full_check():
    load_dotenv()
    print("=== ENVIRONMENT DIAGNOSTIC ===")
    
    # 1. Database
    db_url = os.getenv("DATABASE_URL", "NOT_FOUND")
    if "neon.tech" in db_url.lower():
         print("DB: [NEON DETECTED] This is a cloud database.")
    elif "localhost" in db_url.lower() or "127.0.0.1" in db_url.lower():
         print("DB: [LOCAL DETECTED] This is your local PostgreSQL.")
    else:
         print(f"DB: {db_url[:30]}...")

    # 2. Google Sheets
    cred_id = os.getenv("GOOGLE_SHEET_ID", "NOT_FOUND")
    print(f"SHEET_ID: {cred_id}")
    
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
    print(f"JSON Length: {len(creds_json)}")
    
    if creds_json:
        try:
            creds_json = creds_json.strip()
            # Common issue: wrapped in single quotes in .env
            if creds_json.startswith("'") and creds_json.endswith("'"):
                 creds_json = creds_json[1:-1]
            
            data = json.loads(creds_json)
            print("JSON Status: VALID JSON")
            print(f"Service Account: {data.get('client_email')}")
        except Exception as e:
             print(f"JSON Status: INVALID! Error: {e}")
             print("First 20 chars of JSON:", creds_json[:20])
    else:
        print("JSON Status: EMPTY")

if __name__ == "__main__":
    full_check()
