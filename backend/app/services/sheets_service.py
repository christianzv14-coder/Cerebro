import gspread
from oauth2client.service_account import ServiceAccountCredentials
from app.core.config import settings
from datetime import date
import json

def get_sheet():
    try:
        creds_json = settings.GOOGLE_SHEETS_CREDENTIALS_JSON
        if not creds_json:
            import os
            creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
            
        if not creds_json:
            print("ERROR [SHEETS] No se encontraron credenciales en GOOGLE_SHEETS_CREDENTIALS_JSON")
            return None
        
        creds_json = creds_json.strip()
        if creds_json.startswith("'") or creds_json.startswith('"'):
            creds_json = creds_json[1:-1]
        
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(settings.GOOGLE_SHEET_ID)
    except Exception as e:
        print(f"ERROR [SHEETS] Falló la autenticación: {e}")
        return None

def normalize_sheet_date(date_val):
    if not date_val: return ""
    s = str(date_val).strip()
    try:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                dt = date.fromisoformat(s) if fmt=="%Y-%m-%d" else date.strptime(s, fmt)
                return dt.strftime("%Y-%m-%d")
            except: continue
        return s
    except: return s

def sync_activity_to_sheet(activity):
    """Updates a row in the Bitacora sheet when an activity is started or finished."""
    print(f"\n>>> [SHEETS START] Syncing activity {activity.ticket_id}...")
    try:
        sheet = get_sheet()
        if not sheet: return

        year = activity.fecha.year
        bitacora_title = f"Bitacora {year}"
        try:
            ws = sheet.worksheet(bitacora_title)
        except gspread.WorksheetNotFound:
            try: ws = sheet.worksheet("Bitacora")
            except: return

        all_rows = ws.get_all_values()
        if not all_rows: return
        headers = [h.strip().lower() for h in all_rows[0]]
        
        # Column mapping based on screenshot:
        # Año, Fecha Plan, Fecha Cierre, Ticket ID, Tecnico, Patente, Cliente, Direccion, Tipo Trabajo, Estado Final
        try:
            ticket_col = -1
            for c in ["ticket id", "ticket_id", "ticket"]:
                if c in headers: ticket_col = headers.index(c); break
                
            state_col = -1
            for c in ["estado final", "estado_final", "estado"]:
                if c in headers: state_col = headers.index(c) + 1; break

            # Optional headers
            start_col = -1
            for c in ["inicio", "hora inicio", "fecha inicio"]:
                if c in headers: start_col = headers.index(c) + 1; break
            
            end_col = -1
            for c in ["hora fin", "fin", "fecha cierre", "fecha_cierre"]:
                if c in headers: end_col = headers.index(c) + 1; break

            obs_col = -1
            for c in ["observacion", "observaciones", "notas"]:
                if c in headers: obs_col = headers.index(c) + 1; break

            motivo_col = -1
            for c in ["motivo", "motivo fallido", "motivo fallo", "motivo_fallido", "resultado_motivo"]:
                if c in headers: motivo_col = headers.index(c) + 1; break

            # New Fields Config
            prioridad_col = -1
            if "prioridad" in headers: prioridad_col = headers.index("prioridad") + 1
            
            acc_col = -1
            if "accesorios" in headers: acc_col = headers.index("accesorios") + 1
            
            comuna_col = -1
            if "comuna" in headers: comuna_col = headers.index("comuna") + 1
            
            region_col = -1
            if "region" in headers: region_col = headers.index("region") + 1

        except Exception as e:
            print(f"DEBUG [SHEETS] Error mapping columns: {e}")
            return

        if ticket_col == -1 or state_col == -1:
            print(f"DEBUG [SHEETS] Required columns not found: Ticket={ticket_col}, State={state_col}")
            return

        target_ticket = activity.ticket_id.strip().upper()
        found = False
        for i, row in enumerate(all_rows[1:], start=2):
            if len(row) > ticket_col and row[ticket_col].strip().upper() == target_ticket:
                print(f"  [MATCH] Ticket {target_ticket} found in row {i}. Updating...")
                
                # Update standard fields
                ws.update_cell(i, state_col, str(activity.estado.value if hasattr(activity.estado, "value") else activity.estado))
                
                if start_col != -1 and activity.hora_inicio:
                    ws.update_cell(i, start_col, str(activity.hora_inicio))
                if end_col != -1 and activity.hora_fin:
                    ws.update_cell(i, end_col, str(activity.hora_fin))
                if obs_col != -1 and activity.observacion:
                    ws.update_cell(i, obs_col, str(activity.observacion))
                if motivo_col != -1 and activity.resultado_motivo:
                    ws.update_cell(i, motivo_col, str(activity.resultado_motivo))
                
                # Update new fields (Always update if column exists, as these are static from plan)
                if prioridad_col != -1 and activity.prioridad:
                    ws.update_cell(i, prioridad_col, str(activity.prioridad))
                if acc_col != -1 and activity.accesorios:
                    ws.update_cell(i, acc_col, str(activity.accesorios))
                if comuna_col != -1 and activity.comuna:
                    ws.update_cell(i, comuna_col, str(activity.comuna))
                if region_col != -1 and activity.region:
                    ws.update_cell(i, region_col, str(activity.region))

                found = True
                break
        
        if not found:
             print(f"  [NOT FOUND] Ticket {target_ticket} not in sheet. Appending...")
             # New row structure: Año, Fecha Plan, Fecha Cierre, Ticket ID, Tecnico, Patente, Cliente, Direccion, Tipo Trabajo, Estado Final
             # We need to map which index belongs to which column for the new row.
             # This is a bit complex for append, traditionally we append in a fixed order.
             # Standard order based on requirement: 
             # Año(0), Fecha Plan(1), Fecha Cierre(2), Ticket ID(3), Tecnico(4), Patente(5), Cliente(6), Direccion(7), Tipo Trabajo(8), Estado Final(9)
             new_row = ["" for _ in range(len(headers))]
             
             # Map headers to new row indices
             mapping = {
                 "año": str(activity.fecha.year),
                 "fecha plan": str(activity.fecha),
                 "ticket id": activity.ticket_id,
                 "tecnico": activity.tecnico_nombre,
                 "patente": activity.patente,
                 "cliente": activity.cliente,
                 "direccion": activity.direccion,
                 "tipo trabajo": activity.tipo_trabajo,
                 "estado final": str(activity.estado.value if hasattr(activity.estado, "value") else activity.estado),
                 # New fields mapping
                 "prioridad": str(activity.prioridad or ""),
                 "accesorios": str(activity.accesorios or ""),
                 "comuna": str(activity.comuna or ""),
                 "region": str(activity.region or "")
             }
             
             for h_idx, h_name in enumerate(headers):
                 if h_name in mapping:
                     new_row[h_idx] = mapping[h_name]
             
             ws.append_row(new_row)
             print(f"DEBUG [SHEETS] New row appended for {target_ticket}.")

        print(f"DEBUG [SHEETS] Activity sync DONE.")
    except Exception as e:
        print(f"ERROR [SHEETS] Activity sync failed: {e}")

def sync_signature_to_sheet(signature):
    print(f"\n>>> [SHEETS START] Syncing signature for {signature.tecnico_nombre}...")
    try:
        sheet = get_sheet()
        if not sheet: return

        year = signature.fecha.year
        today_iso = str(signature.fecha)
        tech_target = signature.tecnico_nombre.strip().lower()

        # 1. Update Firmas
        firmas_title = f"Firmas {year}"
        try:
            ws_firmas = sheet.worksheet(firmas_title)
        except gspread.WorksheetNotFound:
            ws_firmas = sheet.add_worksheet(title=firmas_title, rows=1000, cols=5)
            ws_firmas.append_row(["Fecha", "Tecnico", "Timestamp", "Referencia Firma"])
        
        ws_firmas.append_row([today_iso, signature.tecnico_nombre, str(signature.timestamp), signature.signature_ref])
        print(f"DEBUG [SHEETS] Signature appended to '{firmas_title}'")

        # 2. Update Bitacora 'Firmado' column
        bitacora_title = f"Bitacora {year}"
        try:
            ws_bitacora = sheet.worksheet(bitacora_title)
        except gspread.WorksheetNotFound:
            try: ws_bitacora = sheet.worksheet("Bitacora")
            except: return

        all_rows = ws_bitacora.get_all_values()
        if not all_rows: return
        headers = [h.strip().lower() for h in all_rows[0]]
        
        date_col = -1
        for c in ["fecha plan", "fecha", "fecha_plan"]:
            if c in headers: date_col = headers.index(c); break
        tech_col = -1
        for c in ["tecnico", "técnico", "tecnico_nombre"]:
            if c in headers: tech_col = headers.index(c); break

        if date_col == -1 or tech_col == -1: return

        # Find columns for 'firmado' and 'fecha cierre'
        try:
            sign_col = headers.index("firmado") + 1
        except ValueError:
            sign_col = len(headers) + 1
            ws_bitacora.update_cell(1, sign_col, "Firmado")

        close_date_col = -1
        for c in ["fecha cierre", "fecha_cierre", "cierre"]:
            if c in headers: close_date_col = headers.index(c) + 1; break

        # Prepare batch update
        cells_to_update = []
        for i, row in enumerate(all_rows[1:], start=2):
            if len(row) > max(date_col, tech_col):
                if normalize_sheet_date(row[date_col]) == today_iso and str(row[tech_col]).strip().lower() == tech_target:
                    print(f"  [MATCH] Found row {i} for tech {tech_target}. Adding to batch...")
                    # Update Firmado
                    from gspread import Cell
                    cells_to_update.append(Cell(row=i, col=sign_col, value="FIRMADO"))
                    # Update Fecha Cierre
                    if close_date_col != -1:
                        cells_to_update.append(Cell(row=i, col=close_date_col, value=str(signature.timestamp)))
        
        if cells_to_update:
            ws_bitacora.update_cells(cells_to_update)
            print(f"DEBUG [SHEETS] Batch update of {len(cells_to_update)} cells DONE.")
        else:
            print(f"DEBUG [SHEETS] No rows found to update for signature sync.")

        print("DEBUG [SHEETS] Signature update in Bitacora DONE.")
    except Exception as e:
        print(f"ERROR [SHEETS] Signature sync failed: {e}")
