import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from dotenv import load_dotenv

load_dotenv()

def debug_minimal():
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json: 
        print("NO CREDS")
        return
        
    if creds_json.startswith("'") or creds_json.startswith('"'):
        creds_json = creds_json[1:-1]
    
    creds_dict = json.loads(creds_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    sheet = client.open_by_key(sheet_id)
    
    # Try finding the active bitacora
    try: ws = sheet.worksheet(f"Bitacora {2025}")
    except:
         try: ws = sheet.worksheet(f"Bitacora {2024}")
         except: ws = sheet.worksheet("Bitacora")
         
    rows = ws.get_all_values()
    headers = [str(h).strip().lower() for h in rows[0]]
    
    idx_firmado = -1
    idx_estado = -1
    
    for i, h in enumerate(headers):
        if "firmado" in h: idx_firmado = i
        if "estado" == h or "status" == h: idx_estado = i # Strict match to avoid partials like 'estado pago'
        
    print(f"INDICES FOUND: Firmado={idx_firmado}, Estado={idx_estado}")
    
    for i, row in enumerate(rows[1:], start=2):
        row_str = str(row).upper()
        if "JUAN" in row_str:
            print(f"ROW {i} (JUAN):")
            
            val_est = "N/A"
            if idx_estado != -1 and len(row) > idx_estado:
                val_est = row[idx_estado]
                
            val_firm = "N/A"
            if idx_firmado != -1 and len(row) > idx_firmado:
                 val_firm = row[idx_firmado]
                 
            print(f"  ESTADO: '{val_est}'")
            print(f"  FIRMADO: '{val_firm}'")

if __name__ == "__main__":
    debug_minimal()
