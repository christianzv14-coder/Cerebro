import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import logging
from datetime import datetime
from app.core.points_calculator import calculate_final_score

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sheet_client():
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        logger.error("No creds found.")
        return None
    
    try:
        creds_json = creds_json.strip()
        if creds_json.startswith("'") or creds_json.startswith('"'):
            creds_json = creds_json[1:-1]
        
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logger.error(f"Auth failed: {e}")
        return None

def normalize_header(h):
    return h.strip().lower()

def update_scores_in_sheet():
    """
    Main function to read Bitacora and update Puntajes.
    Can be called from API as a background task.
    """
    logger.info(">>> [SCORES] Starting score update...")
    client = get_sheet_client()
    if not client: 
        logger.error(">>> [SCORES] No client, aborting.")
        return

    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    try:
        sheet = client.open_by_key(sheet_id)
    except Exception as e:
        logger.error(f">>> [SCORES] Sheet open failed: {e}")
        return
    
    # 1. Read Bitacora
    current_year = datetime.now().year
    bitacora_ws_name = f"Bitacora {current_year}"
    try:
        ws_bitacora = sheet.worksheet(bitacora_ws_name)
    except:
        try:
            ws_bitacora = sheet.worksheet("Bitacora 2024") # Fallback
        except:
            logger.error("Bitacora sheet not found.")
            return

    all_values = ws_bitacora.get_all_values()
    if not all_values:
        logger.error("Bitacora is empty.")
        return

    headers = [normalize_header(h) for h in all_values[0]]
    data_rows = all_values[1:]
    
    try:
        idx_ticket = headers.index("ticket id")
        idx_tecnico = headers.index("tecnico") 
        # Fallback for tecnico variants if needed
        
        idx_fecha = headers.index("fecha plan")
        idx_accesorios = headers.index("accesorios")
        idx_region = headers.index("region")
        idx_tipo = headers.index("tipo trabajo")
    except ValueError as e:
        logger.error(f"Missing required column in Bitacora: {e}. Headers found: {headers}")
        return

    # 2. Group by Ticket ID to count technicians
    ticket_counts = {}
    for row in data_rows:
        if len(row) <= idx_ticket: continue
        t_id = row[idx_ticket].strip().upper()
        if not t_id: continue
        ticket_counts[t_id] = ticket_counts.get(t_id, 0) + 1

    # 3. Process Rows
    output_rows = []
    output_headers = [
        "Fecha", "Ticket ID", "Técnico", "Tipo Trabajo", "Accesorios", 
        "Items Detectados", "Región", "FDS?", 
        "Puntos Base", "Mult. Región", "Mult. FDS", "N° Técnicos", "Puntos Finales", "Dinero"
    ]
    output_rows.append(output_headers)
    
    total_money = 0
    
    for row in data_rows:
        if len(row) <= idx_ticket: continue
        
        t_id = row[idx_ticket].strip().upper()
        if not t_id: continue
        
        tecnico = row[idx_tecnico] if len(row) > idx_tecnico else ""
        fecha = row[idx_fecha] if len(row) > idx_fecha else ""
        accesorios = row[idx_accesorios] if len(row) > idx_accesorios else ""
        region = row[idx_region] if len(row) > idx_region else ""
        tipo = row[idx_tipo] if len(row) > idx_tipo else ""
        
        tech_count = ticket_counts.get(t_id, 1)
        
        row_data = {
            "Accesorios": accesorios,
            "Region": region,
            "Fecha Plan": fecha
        }
        
        res = calculate_final_score(row_data, tech_count)
        
        out_row = [
            fecha,
            t_id,
            tecnico,
            tipo,
            accesorios,
            res["items"],
            region,
            "SI" if res["mult_weekend"] > 1.0 else "NO",
            res["base_points"],
            res["mult_region"],
            res["mult_weekend"],
            res["tech_count"],
            res["final_points"],
            res["money"]
        ]
        output_rows.append(out_row)
        total_money += res["money"]

    # 4. Write to "Puntajes"
    puntajes_ws_name = "Puntajes"
    try:
        ws_puntajes = sheet.worksheet(puntajes_ws_name)
        ws_puntajes.clear()
    except:
        ws_puntajes = sheet.add_worksheet(title=puntajes_ws_name, rows=1000, cols=20)
    
    ws_puntajes.update(output_rows)
    logger.info(f">>> [SCORES] Updated {len(output_rows)-1} rows. Total: ${total_money}")
