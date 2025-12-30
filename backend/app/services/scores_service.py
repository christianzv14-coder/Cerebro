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
    Update logic with DB Access to check Signatures.
    Only writes row if Technician has SIGNED that day.
    Only counts points if Activity is EXITOSO (handled by calculator, passed via header 'Estado').
    """
    logger.info(">>> [SCORES] Starting score update...")
    
    # Imports inside function to avoid circular deps if any
    from app.database import SessionLocal
    from app.models.models import DaySignature
    
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
        logger.error("Bitacora sheet not found.")
        return

    all_values = ws_bitacora.get_all_values()
    if not all_values:
        logger.error("Bitacora is empty.")
        return

    headers = [normalize_header(h) for h in all_values[0]]
    data_rows = all_values[1:]
    
    # Find headers
    try:
        idx_ticket = headers.index("ticket id")
        idx_tecnico = headers.index("tecnico") 
        idx_fecha = headers.index("fecha plan")
        idx_accesorios = headers.index("accesorios")
        idx_region = headers.index("region")
        idx_tipo = headers.index("tipo trabajo")
        # Try to find 'estado' or 'status'
        idx_estado = -1
        if "estado" in headers: idx_estado = headers.index("estado")
        elif "status" in headers: idx_estado = headers.index("status")
        
    except ValueError as e:
        logger.error(f"Missing required column in Bitacora: {e}. Headers found: {headers}")
        return

    # Remove DB Signature Check
    # We now trust the 'Firmado' column in the Sheet itself, as populated by the App.
    
    # Try to find 'firmado' column
    idx_firmado = -1
    try:
        if "firmado" in headers: idx_firmado = headers.index("firmado")
    except:
        pass

    # 3. Group by Ticket ID
    ticket_counts = {}
    for row in data_rows:
        if len(row) <= idx_ticket: continue
        t_id = row[idx_ticket].strip().upper()
        if not t_id: continue
        ticket_counts[t_id] = ticket_counts.get(t_id, 0) + 1

    # 4. Process Rows
    output_rows = []
    output_headers = [
        "Fecha", "Ticket ID", "Técnico", "Tipo Trabajo", "Accesorios", 
        "Items Detectados", "Región", "FDS?", 
        "Puntos Base", "Mult. Región", "Mult. FDS", "N° Técnicos", "Puntos Finales", "Dinero"
    ]
    output_rows.append(output_headers)
    
    total_money = 0
    rows_skipped = 0
    
    for row_idx, row in enumerate(data_rows):
        if len(row) <= idx_ticket: continue
        
        t_id = row[idx_ticket].strip().upper()
        if not t_id: continue
        
        raw_tech = row[idx_tecnico] if len(row) > idx_tecnico else "-"
        raw_date = row[idx_fecha] if len(row) > idx_fecha else ""
        
        tecnico = str(raw_tech).strip().upper()
        fecha_str = str(raw_date).strip()
        
        # --- CHECK SIGNATURE VIA SHEET COLUMN ---
        is_signed = False
        if idx_firmado != -1 and len(row) > idx_firmado:
            val_firmado = str(row[idx_firmado]).strip().upper()
            if "FIRMADO" in val_firmado:
                is_signed = True
        
        # Fallback: If tech/date matching (legacy) logic is needed, we could add it back,
        # but user specifically said "sale directo la pestaña bitacora". relying on that column is safer.
        
        if not is_signed:
            rows_skipped += 1
            if rows_skipped < 5:
                logger.debug(f"Skipping row {row_idx}: Tech '{tecnico}' NOT MARKED 'FIRMADO' in Sheet.")
            continue
            
        # If Signed, Calculate Points
        accesorios = row[idx_accesorios] if len(row) > idx_accesorios else ""
        region = row[idx_region] if len(row) > idx_region else ""
        tipo = row[idx_tipo] if len(row) > idx_tipo else ""
        
        estado = "PENDIENTE"
        if idx_estado != -1 and len(row) > idx_estado:
            estado = row[idx_estado]

        tech_count = ticket_counts.get(t_id, 1)
        
        row_data = {
            "Accesorios": accesorios,
            "Region": region,
            "Fecha Plan": fecha,
            "Tipo Trabajo": tipo,
            "Estado": estado # Passed to calculator
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
        try:
            ws_puntajes = sheet.worksheet(puntajes_ws_name)
            ws_puntajes.clear()
        except:
             ws_puntajes = sheet.add_worksheet(title=puntajes_ws_name, rows=1000, cols=20)
        
        if len(output_rows) > 0:
            ws_puntajes.update(output_rows)
        else:
            # If empty (no signatures), just write headers
            ws_puntajes.update([output_headers])
            
        logger.info(f">>> [SCORES] Updated {len(output_rows)-1} rows. Total: ${total_money}")
        
    except Exception as e:
        logger.error(f">>> [SCORES] Write failed: {e}")
