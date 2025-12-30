import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def inspect_pedro():
    print("--- INSPECTING BITACORA FOR PEDRO PASCAL ---")
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json: return

    creds_dict = json.loads(creds_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    sheet = client.open_by_key(sheet_id)
    
    current_year = datetime.now().year
    try:
        ws = sheet.worksheet(f"Bitacora {current_year}")
    except:
        ws = sheet.worksheet("Bitacora")

    all_values = ws.get_all_values()
    headers = [h.lower().strip() for h in all_values[0]]
    print(f"HEADERS FOUND: {headers}")
    
    # Check logical columns
    try: idx_tecnico = headers.index("tecnico")
    except: idx_tecnico = -1
    
    candidates = ["estado", "estado final", "status"]
    idx_estado = -1
    for c in candidates:
        if c in headers:
            idx_estado = headers.index(c)
            print(f"USING STATUS COLUMN: '{c}' (Index {idx_estado})")
            break
            
    idx_firmado = -1
    if "firmado" in headers: idx_firmado = headers.index("firmado")
    
    idx_motivo = -1
    if "motivo fallo" in headers: idx_motivo = headers.index("motivo fallo")

    for row_idx, row in enumerate(all_values[1:], start=2):
        if idx_tecnico != -1 and len(row) > idx_tecnico:
            tech = row[idx_tecnico].strip().upper()
            if "PEDRO PASCAL" in tech:
                print(f"\n--- ROW {row_idx} MATCH: {tech} ---")
                print(f"Full Row: {row}")
                
                # Check Status
                val_estado = row[idx_estado] if idx_estado != -1 and len(row) > idx_estado else "N/A"
                print(f"  > STATUS VALUE (Raw): '{val_estado}'")
                
                # Check Firmado
                val_firmado = row[idx_firmado] if idx_firmado != -1 and len(row) > idx_firmado else "N/A"
                print(f"  > FIRMADO VALUE: '{val_firmado}'")
                
                # Check Motivo
                val_motivo = row[idx_motivo] if idx_motivo != -1 and len(row) > idx_motivo else "N/A"
                print(f"  > MOTIVO VALUE: '{val_motivo}'")

                # Simulate Logic
                is_signed = "FIRMADO" in val_firmado.upper()
                is_failed = False
                if any(x in val_estado.upper() for x in ["FALLIDO", "CANCELADO", "REPROGRAMADO", "NULA"]):
                    is_failed = True
                
                print(f"  > LOGIC TEST: Signed={is_signed}, FailedDetected={is_failed}")
                
                if is_signed and not is_failed:
                     print("  > RESULT: WOULD FORCE EXITOSO (POINTS AWARDED) -> WARNING")
                elif is_signed and is_failed:
                     print("  > RESULT: CORRECTLY DETECTED FAILURE (0 POINTS)")

if __name__ == "__main__":
    inspect_pedro()
