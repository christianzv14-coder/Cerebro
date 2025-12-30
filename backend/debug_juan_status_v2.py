import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Import is fine, assuming points_calculator exists
from app.core.points_calculator import calculate_final_score

load_dotenv()

def normalize_header(h):
    return h.strip().lower()

def check_juan_status():
    log_messages = []
    def log(msg):
        print(msg)
        log_messages.append(str(msg))

    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        log("No creds found.")
        return

    creds_dict = json.loads(creds_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    sheet = client.open_by_key(sheet_id)
    
    current_year = datetime.now().year
    # Try 2024 if needed, but assuming current
    bitacora_ws_name = f"Bitacora {current_year}"
    try:
        ws_bitacora = sheet.worksheet(bitacora_ws_name)
    except:
        ws_bitacora = sheet.worksheet("Bitacora 2024")

    all_values = ws_bitacora.get_all_values()
    headers = [normalize_header(h) for h in all_values[0]]
    data_rows = all_values[1:]
    
    log(f"Headers: {headers}")
    
    idx_ticket = headers.index("ticket id")
    idx_tecnico = headers.index("tecnico")
    idx_fecha = headers.index("fecha plan")
    idx_accesorios = headers.index("accesorios")
    idx_region = headers.index("region")
    idx_tipo = headers.index("tipo trabajo")
    idx_firmado = headers.index("firmado") if "firmado" in headers else -1
    idx_estado = -1
    if "estado" in headers: idx_estado = headers.index("estado")
    elif "estado final" in headers: idx_estado = headers.index("estado final")
    elif "status" in headers: idx_estado = headers.index("status")
    
    target_users = ["JUAN PEREZ", "PEDRO"] 
    
    for row in data_rows:
        if len(row) <= idx_tecnico: continue
        tech_name = row[idx_tecnico].strip().upper()
        
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
            estado_raw = row[idx_estado].strip()
            
        log(f"\n>> TECH: {tech_name} | ID: {t_id}")
        log(f"   Estado Raw: ||{estado_raw}||")
        log(f"   Firmado Raw: ||{val_firmado}|| -> Signed: {is_signed}")
        
        # Simulate NEW Logic
        calc_estado = "PENDIENTE"
        if is_signed:
            # FIX LOGIC CHECK
            failure_terms = ["FALLIDO", "CANCELADO", "REPROGRAMADO", "NULA", "FALLIDA"]
            if estado_raw and any(x in estado_raw.upper() for x in failure_terms):
                calc_estado = estado_raw 
                log(f"  [NEW LOGIC] Signed but Status '{estado_raw}' -> Keeping as Fallido (0 pts)")
            else:
                calc_estado = "EXITOSO"
                log("  [NEW LOGIC] Signed & Not Failed -> Forced to EXITOSO")
        else:
            log("  [NEW LOGIC] Not Signed.")

        row_data = {
            "Accesorios": row[idx_accesorios] if len(row) > idx_accesorios else "",
            "Region": row[idx_region] if len(row) > idx_region else "",
            "Fecha Plan": row[idx_fecha] if len(row) > idx_fecha else "",
            "Tipo Trabajo": row[idx_tipo] if len(row) > idx_tipo else "",
            "Estado": calc_estado
        }
        res = calculate_final_score(row_data, 1)
        log(f"  > Points: {res['final_points']}")

    with open("debug_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log_messages))

if __name__ == "__main__":
    check_juan_status()
