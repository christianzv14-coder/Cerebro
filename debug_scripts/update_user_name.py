
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Setup
load_dotenv('backend/.env')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
CREDS_JSON = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')

def update_config_name():
    if not GOOGLE_SHEET_ID or not CREDS_JSON:
        print("Missing credentials.")
        return
    
    try:
        import base64
        creds_str = CREDS_JSON
        if not creds_str.strip().startswith('{'):
            try:
                creds_str = base64.b64decode(creds_str).decode('utf-8')
            except: pass
            
        creds_dict = json.loads(creds_str)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key(GOOGLE_SHEET_ID)
        
        try:
            ws_config = sh.worksheet("Config")
            data = ws_config.get_all_records()
            print(f"Current Config Data: {data}")
            
            # Find the row for 'Nombre' or 'Name'
            row_idx = 1
            found = False
            for i, row in enumerate(data):
                key = str(row.get("Key", "")).lower()
                if "nombre" in key or "name" in key:
                    row_idx = i + 2 # +1 for 1-indexing, +1 for header
                    found = True
                    break
            
            if found:
                print(f"Updating row {row_idx} to 'Christian ZV'...")
                ws_config.update_cell(row_idx, 2, "Christian ZV")
                print("Update successful.")
            else:
                print("Key 'Nombre'/'Name' not found in Config sheet.")
                
        except Exception as e:
            print(f"Error updating Config: {e}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_config_name()
