import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from app.core.points_calculator import calculate_final_score

load_dotenv()

def normalize_header(h):
    return h.strip().lower()

def check_juan_status():
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
    
    current_year = datetime.now().year
    bitacora_ws_name = f"Bitacora {current_year}"
    ws_bitacora = sheet.worksheet(bitacora_ws_name)
    
    all_values = ws_bitacora.get_all_values()
    headers = [normalize_header(h) for h in all_values[0]]
    data_rows = all_values[1:]
    
    # Indices
    idx_ticket = headers.index("ticket id")
    idx_tecnico = headers.index("tecnico")
    idx_fecha = headers.index("fecha plan")
    idx_accesorios = headers.index("accesorios")
    idx_region = headers.index("region")
    idx_tipo = headers.index("tipo trabajo")
    idx_firmado = headers.index("firmado") if "firmado" in headers else -1
    idx_estado = -1
    if "estado" in headers: idx_estado = headers.index("estado")
    elif "status" in headers: idx_estado = headers.index("status")

    print("--- HEADERS ANALYSIS ---")
    for i, h in enumerate(headers):
        print(f"[{i}] {h}")
    
    print(f"Estado index: {idx_estado}, Firmado index: {idx_firmado}")

    target_users = ["JUAN PEREZ", "PEDRO"] 
    
    for row in data_rows:
        if len(row) <= idx_tecnico: continue
        tech_name = row[idx_tecnico].strip().upper()
        
        # Check if match partial
        matched = False
        for u in target_users:
            if u in tech_name:
                matched = True
        
        if not matched: continue
        
        t_id = row[idx_ticket]
        is_signed = False
        val_firmado = ""
        if idx_firmado != -1 and len(row) > idx_firmado:
            val_firmado = str(row[idx_firmado]).strip().upper()
            if "FIRMADO" in val_firmado:
                is_signed = True
                
        estado_raw = ""
        if idx_estado != -1 and len(row) > idx_estado:
            estado_raw = row[idx_estado]
            
        print(f"\n>> TECH: {tech_name} | ID: {t_id}")
        print(f"   Estado Raw: ||{estado_raw}||")
        print(f"   Firmado Raw: ||{val_firmado}|| -> Signed: {is_signed}")
        
        # Simulate NEW Logic
        calc_estado = "PENDIENTE"
        if is_signed:
            # FIX applied
            print(f"  [CHECK] Comparing '{estado_raw.upper()}' with failure terms.")
            if estado_raw and any(x in estado_raw.upper() for x in ["FALLIDO", "CANCELADO", "REPROGRAMADO", "NULA"]):
                calc_estado = estado_raw 
                print(f"  [NEW LOGIC] Signed but Status '{estado_raw}' -> Keeping as Fallido (0 pts)")
            else:
                calc_estado = "EXITOSO"
                print("  [NEW LOGIC] Signed & Not Failed -> Forced to EXITOSO")
        else:
            print("  [NEW LOGIC] Not Signed.")
            
        # Calc
        row_data = {
            "Accesorios": row[idx_accesorios] if len(row) > idx_accesorios else "",
            "Region": row[idx_region] if len(row) > idx_region else "",
            "Fecha Plan": row[idx_fecha] if len(row) > idx_fecha else "",
            "Tipo Trabajo": row[idx_tipo] if len(row) > idx_tipo else "",
            "Estado": calc_estado
        }
        res = calculate_final_score(row_data, 1) # simple tech count 1 for debug
        print(f"  > Points: {res['final_points']} (Money: {res['money']})")
        
        if "FALLIDO" in estado_raw.upper() and res['final_points'] > 0:
            print("  !!! BUG CONFIRMED: Failed status but Points > 0 !!!")
        elif "FALLIDO" in estado_raw.upper() and res['final_points'] == 0:
             print("  OK: Failed status and 0 Points.")

if __name__ == "__main__":
    check_juan_status()
