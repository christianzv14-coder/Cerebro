import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from dotenv import load_dotenv

load_dotenv()

def debug_juan():
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json: return

    try:
        if creds_json.startswith("'") or creds_json.startswith('"'):
            creds_json = creds_json[1:-1]
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        sheet = client.open_by_key(sheet_id)
        
        # Try finding the active bitacora
        ws = None
        try:
             ws = sheet.worksheet(f"Bitacora {2025}")
        except:
             try: ws = sheet.worksheet(f"Bitacora {2024}")
             except: ws = sheet.worksheet("Bitacora")
             
        rows = ws.get_all_values()
        headers = [str(h).strip().lower() for h in rows[0]]
        
        print("--- HEADERS ---")
        idx_firmado = -1
        idx_estado = -1
        idx_accesorios = -1
        
        for i, h in enumerate(headers):
            print(f"{i}: {h}")
            if "firmado" in h: idx_firmado = i
            if "estado" in h or "status" in h: idx_estado = i
            if "accesorios" in h: idx_accesorios = i
            
        print(f"\nINDICES: Firmado={idx_firmado}, Estado={idx_estado}")

        print("\n--- SEARCHING FOR JUAN ---")
        for i, row in enumerate(rows[1:], start=2):
            row_str = str(row).upper()
            if "JUAN" in row_str:
                print(f"\nFOUND JUAN AT ROW {i}")
                
                val_firmado = row[idx_firmado] if idx_firmado != -1 and len(row) > idx_firmado else "N/A"
                val_estado = row[idx_estado] if idx_estado != -1 and len(row) > idx_estado else "N/A"
                
                print(f"ESTADO (Col {idx_estado}): '{val_estado}'")
                print(f"FIRMADO (Col {idx_firmado}): '{val_firmado}'")
                print(f"FULL ROW (truncated): {str(row)[:100]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_juan()
