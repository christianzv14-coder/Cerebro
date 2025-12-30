import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from dotenv import load_dotenv

load_dotenv()

def inspect():
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        print("No creds.")
        return

    creds_json = creds_json.strip()
    if creds_json.startswith("'") or creds_json.startswith('"'):
        creds_json = creds_json[1:-1]
    
    creds_dict = json.loads(creds_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    sheet = client.open_by_key(sheet_id)
    
    # Try year or default
    try:
        ws = sheet.worksheet(f"Bitacora {2025}")
    except:
        try:
             ws = sheet.worksheet(f"Bitacora {2024}")
        except:
             ws = sheet.worksheet("Bitacora")

    rows = ws.get_all_values()
    print(f"SHEET NAME: {ws.title}")
    
    headers = [str(h).strip().lower() for h in rows[0]]
    print(f"HEADERS: {headers}")
    
    try:
        idx_firmado = headers.index("firmado")
        print(f"idx_firmado: {idx_firmado}")
    except:
        print("idx_firmado: NOT FOUND")
        
    try:
        idx_estado = -1
        if "estado" in headers: idx_estado = headers.index("estado")
        elif "status" in headers: idx_estado = headers.index("status")
        print(f"idx_estado: {idx_estado}")
    except:
        print("idx_estado: NOT FOUND")

    print("\nscanning for 'FIRMADO' rows...")
    found = 0
    for i, r in enumerate(rows[1:], start=2):
        if found > 3: break
        
        # Check signed
        is_signed = False
        val_firm = "N/A"
        try:
            if idx_firmado != -1:
                val_firm = r[idx_firmado]
                if "FIRMADO" in str(val_firm).upper():
                    is_signed = True
        except: pass
        
        if is_signed:
            val_stat = "N/A"
            if idx_estado != -1: val_stat = r[idx_estado]
            
            print(f"ROW {i}: Signed={val_firm} | Estado='{val_stat}' | Full: {r}")
            found += 1

if __name__ == "__main__":
    inspect()
