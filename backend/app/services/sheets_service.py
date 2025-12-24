import gspread
from oauth2client.service_account import ServiceAccountCredentials
from app.core.config import settings
from app.models.models import Activity
import json
import os

# Scope needed
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_client():
    if not settings.GOOGLE_SHEETS_CREDENTIALS_JSON:
        print("Warning: GOOGLE_SHEETS_CREDENTIALS_JSON not set.")
        return None
    
    # Parse JSON from env var string directly or load from file? 
    # For robust deployment, env var usually holds the json string or path.
    # User instructions implied Env Var setup. Let's assume it's a file path or JSON content.
    # If it starts with '{', treat as content. Else path.
    coords = settings.GOOGLE_SHEETS_CREDENTIALS_JSON
    
    try:
        if coords.strip().startswith("{"):
             creds_dict = json.loads(coords)
             creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        else:
             if not os.path.exists(coords):
                  print(f"Warning: Credentials file {coords} not found.")
                  return None
             creds = ServiceAccountCredentials.from_json_keyfile_name(coords, SCOPE)
             
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error authenticating Google Sheets: {e}")
        return None

def sync_activity_to_sheet(activity: Activity):
    """
    Upsert row in 'Bitacora {YEAR}' sheet based on ticket_id.
    """
    client = get_client()
    if not client:
        return

    try:
        sheet = client.open_by_key(settings.GOOGLE_SHEET_ID)
    except Exception as e:
        print(f"Error opening Sheet ID {settings.GOOGLE_SHEET_ID}: {e}")
        return

    year = activity.fecha.year
    ws_title = f"Bitacora {year}"
    
    try:
        ws = sheet.worksheet(ws_title)
    except gspread.WorksheetNotFound:
        # Create it? Or assume it exists. Let's create.
        ws = sheet.add_worksheet(title=ws_title, rows=1000, cols=20)
        # Header
        ws.append_row([
            "Año", "Fecha Plan", "Fecha Cierre", "Ticket ID", "Tecnico", 
            "Patente", "Cliente", "Direccion", "Tipo Trabajo", 
            "Estado Final", "Motivo Fallo", "Hora Inicio", "Hora Fin", 
            "Duracion Min", "Observacion"
        ])

    # Data row
    row_data = [
        str(year),
        str(activity.fecha),
        str(activity.updated_at.date()) if activity.updated_at else "",
        str(activity.ticket_id),
        str(activity.tecnico_nombre),
        str(activity.patente or ""),
        str(activity.cliente or ""),
        str(activity.direccion or ""),
        str(activity.tipo_trabajo or ""),
        str(activity.estado.value),
        str(activity.resultado_motivo or ""),
        str(activity.hora_inicio or ""),
        str(activity.hora_fin or ""),
        str(activity.duracion_min or 0),
        str(activity.observacion or "")
    ]

    # UPSERT Logic
    # gspread doesn't have native upsert by key. We need to find the row.
    # Optimization: If high volume, this is slow. 
    # But for MVP (10 activities/tech * N techs) it's acceptable.
    # We look for ticket_id in column 4 (D).
    
    try:
        # Get all ticket_ids (Col 4)
        ticket_ids = ws.col_values(4) 
        try:
            row_idx = ticket_ids.index(str(activity.ticket_id)) + 1 # 1-based
            # Update row
            # ws.update(f"A{row_idx}:O{row_idx}", [row_data]) # gspread update range
            # Range might vary. Safer to verify.
            
            # Using cell update might be safer but slower. 
            # batch_update is better.
            cell_list = ws.range(row_idx, 1, row_idx, len(row_data))
            for i, cell in enumerate(cell_list):
                cell.value = row_data[i]
            ws.update_cells(cell_list)
            
        except ValueError:
            # Not found, Append
            ws.append_row(row_data)
            
    except Exception as e:
        print(f"Error writing to sheet: {e}")

