import sys
import os
# Add current directory to path so it can find 'app'
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from app.core.config import settings

def debug_sheet():
    print(f"DEBUG: Using Sheet ID: {settings.GOOGLE_SHEET_ID}")
    
    # Use the same logic as sheets_service.get_sheet()
    creds_json = settings.GOOGLE_SHEETS_CREDENTIALS_JSON
    if not creds_json:
        creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
    
    if not creds_json:
        # Fallback to file if env is empty
        file_path = "c:/Users/chzam/OneDrive/Desktop/cerebro-patio/Cerebro/backend/actividades-diarias-482221-75ab65299328.json"
        if os.path.exists(file_path):
            with open(file_path) as f:
                creds_dict = json.load(f)
        else:
            print("ERROR: No credentials found.")
            return
    else:
         creds_dict = json.loads(creds_json.strip("'\""))

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    try:
        sheet = client.open_by_key(settings.GOOGLE_SHEET_ID)
        print("✅ Connected to sheet successfully")
        
        for ws_name in ["Config", "Presupuesto", "Gastos"]:
            try:
                ws = sheet.worksheet(ws_name)
                data = ws.get_all_records()
                print(f"\n--- {ws_name} ---")
                print(f"Rows found: {len(data)}")
                if data:
                    print(f"First row: {data[0]}")
            except Exception as e:
                print(f"❌ Error reading {ws_name}: {e}")
                
    except Exception as e:
        print(f"❌ Failed to open sheet: {e}")

if __name__ == "__main__":
    debug_sheet()
