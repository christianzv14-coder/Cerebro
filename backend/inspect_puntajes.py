import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from dotenv import load_dotenv

load_dotenv()

def check_puntajes_sheet():
    print("--- INSPECTING 'PUNTAJES' SHEET ---")
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
    
    try:
        ws = sheet.worksheet("Puntajes")
    except:
        print("Sheet 'Puntajes' not found.")
        return

    all_values = ws.get_all_values()
    headers = [h.lower() for h in all_values[0]]
    print(f"Headers: {headers}")
    
    try:
        idx_tech = headers.index("técnico")
    except:
        idx_tech = 2 # Guess
        
    try:
        idx_points = headers.index("puntos finales")
    except:
        idx_points = -2 # Guess
        
    found = False
    for row in all_values[1:]:
        tech = row[idx_tech].upper() if len(row) > idx_tech else ""
        if "JUAN PEREZ" in tech:
            found = True
            print(f"\nROW FOUND for {tech}:")
            print(f"  Data: {row}")
            points = row[idx_points] if len(row) > idx_points else "N/A"
            print(f"  > POINTS IN SHEET: {points}")
            
    if not found:
        print("Juan Perez not found in Puntajes.")

if __name__ == "__main__":
    check_puntajes_sheet()
