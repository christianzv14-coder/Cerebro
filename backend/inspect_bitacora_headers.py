import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from datetime import datetime

# Load env manually for script
from dotenv import load_dotenv
load_dotenv()

def inspect_bitacora():
    try:
        creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
        if not creds_json:
            print("No creds found.")
            return

        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        sheet = client.open_by_key(sheet_id)
        
        # Try Bitacora 2025 or 2024
        current_year = datetime.now().year
        try:
            ws = sheet.worksheet(f"Bitacora {current_year}")
        except:
            ws = sheet.worksheet("Bitacora 2024")
        
        headers = ws.row_values(1)
        headers = ws.row_values(1)
        with open("headers_utf8.txt", "w", encoding="utf-8") as f:
            f.write("--- HEADERS FOUND ---\n")
            for i, h in enumerate(headers):
                f.write(f"{i}: {h}\n")
            f.write("---------------------\n")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_bitacora()
