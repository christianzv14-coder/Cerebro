import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import base64
from datetime import datetime, date
import pandas as pd

# --- CONFIG ---
def get_local_creds():
    """Retrieve credentials from local environment variables."""
    # Ensure env is loaded (caller should handle load_dotenv)
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    
    if not sheet_id or not creds_json:
        print("❌ [LOCAL SYNC] Missing GOOGLE_SHEET_ID or JSON in .env")
        return None, None

    # Handle Base64
    if not creds_json.strip().startswith("{"):
        try:
            decoded = base64.b64decode(creds_json).decode('utf-8')
            creds_json = decoded
        except Exception as e:
            print(f"⚠️ [LOCAL SYNC] Base64 decode failed: {e}")

    try:
        creds_dict = json.loads(creds_json)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        return sheet_id, creds_dict
    except Exception as e:
        print(f"❌ [LOCAL SYNC] JSON Parsing failed: {e}")
        return None, None

def get_client():
    sheet_id, creds_dict = get_local_creds()
    if not creds_dict: return None, None
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client, sheet_id
    except Exception as e:
        print(f"❌ [LOCAL SYNC] Auth failed: {e}")
        return None, None

def sync_row_to_sheet(row_data):
    """
    Syncs a single Dictionary representing a row to Google Sheets.
    row_data expected keys: ticket_id, fecha, tecnico_nombre, patente, ...
    """
    client, sheet_id = get_client()
    if not client: return

    try:
        sheet = client.open_by_key(sheet_id)
        
        # Determine Year for Sheet Name
        fecha_val = row_data.get("fecha")
        try:
            if isinstance(fecha_val, str):
                dt = datetime.strptime(fecha_val, "%Y-%m-%d")
                year = dt.year
            elif hasattr(fecha_val, "year"):
                year = fecha_val.year
            else:
                year = datetime.now().year
        except:
            year = datetime.now().year

        bitacora_title = f"Bitacora {year}"
        try:
            ws = sheet.worksheet(bitacora_title)
        except gspread.WorksheetNotFound:
            try: ws = sheet.worksheet("Bitacora")
            except: 
                print(f"⚠️ [LOCAL SYNC] Sheet '{bitacora_title}' or 'Bitacora' not found.")
                return

        all_rows = ws.get_all_values()
        if not all_rows: return
        headers = [h.strip().lower() for h in all_rows[0]]

        # Map Columns
        col_map = {}
        for key, possible in {
            "ticket": ["ticket id", "ticket_id", "ticket"],
            "fecha_plan": ["fecha plan", "fecha"],
            "fecha_cierre": ["fecha cierre", "fecha_cierre", "cierre"],
            "tecnico": ["tecnico", "técnico", "tecnico_nombre"],
            "patente": ["patente"],
            "cliente": ["cliente"],
            "direccion": ["direccion"],
            "tipo_trabajo": ["tipo trabajo", "actividad"],
            "estado": ["estado final", "estado"],
            "prioridad": ["prioridad"],
            "accesorios": ["accesorios"],
            "comuna": ["comuna"],
            "region": ["region"]
        }.items():
            col_map[key] = -1
            for p in possible:
                if p in headers: 
                    col_map[key] = headers.index(p)
                    break
        
        ticket_col = col_map["ticket"]
        if ticket_col == -1:
            print("❌ [LOCAL SYNC] 'Ticket ID' column not found.")
            return

        target_ticket = str(row_data.get("ticket_id", "")).strip().upper()
        if not target_ticket: return

        # Search for existing row
        found_idx = -1
        for i, r in enumerate(all_rows[1:], start=2): # 1-based, skip header
            if len(r) > ticket_col and r[ticket_col].strip().upper() == target_ticket:
                found_idx = i
                break
        
        # VALUES TO WRITE
        fields_to_update = {
            "fecha_plan": str(row_data.get("fecha", "")),
            "tecnico": str(row_data.get("tecnico_nombre", "")),
            "patente": str(row_data.get("patente", "")),
            "cliente": str(row_data.get("cliente", "")),
            "direccion": str(row_data.get("direccion", "")),
            "tipo_trabajo": str(row_data.get("tipo_trabajo", "")),
            "prioridad": str(row_data.get("Prioridad", "")),
            "accesorios": str(row_data.get("Accesorios", "")),
            "comuna": str(row_data.get("Comuna", "")),
            "region": str(row_data.get("Region", "")),
        }

        if found_idx != -1:
            # UPDATE
            print(f"   [SYNC] Updating Ticket {target_ticket} at row {found_idx}")
            for key, val in fields_to_update.items():
                c_idx = col_map.get(key, -1)
                if c_idx != -1 and val and val.lower() != "nan":
                    ws.update_cell(found_idx, c_idx + 1, val)
        else:
            # APPEND
            print(f"   [SYNC] Appending New Ticket {target_ticket}")
            new_row = [""] * len(headers)
            
            # Fill mapped columns
            for key, val in fields_to_update.items():
                c_idx = col_map.get(key, -1)
                if c_idx != -1 and val and val.lower() != "nan":
                    new_row[c_idx] = val
            
            # Fill Ticket ID
            new_row[ticket_col] = target_ticket
            
            # Fill State as PENDIENTE default
            st_col = col_map.get("estado", -1)
            if st_col != -1:
                new_row[st_col] = "PENDIENTE"
                
            ws.append_row(new_row)

    except Exception as e:
        print(f"❌ [LOCAL SYNC] Error syncing row: {e}")

def batch_sync_excel(df):
    """
    Iterates a DataFrame and syncs each row.
    """
    print(f"\n--- INICIANDO SINCRONIZACIÓN LOCAL (Robust Backup) ---")
    print(f"ℹ️  Esto asegura que tu Excel se actualice aunque falle el servidor.")
    
    count = 0
    total = len(df)
    
    for index, row in df.iterrows():
        try:
            # Convert row to dict, handling NaNs
            row_dict = row.where(pd.notnull(row), "").to_dict()
            
            # Normalize date
            if "fecha" in row_dict and hasattr(row_dict["fecha"], "strftime"):
                 row_dict["fecha"] = row_dict["fecha"].strftime("%Y-%m-%d")
            
            sync_row_to_sheet(row_dict)
            count += 1
            if count % 5 == 0: print(f"   ... procesando {count}/{total}")
        except Exception as e:
            print(f"   Error fila {index}: {e}")
            
    print(f"✅ Sincronización Local Completada: {count} filas procesadas.")
