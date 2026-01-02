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

def sync_signature_to_sheet(signature, user_email=None):
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
            ws_firmas = sheet.add_worksheet(title=firmas_title, rows=1000, cols=6)
            ws_firmas.append_row(["Fecha", "Tecnico", "Timestamp", "Referencia Firma", "Email", "Estado Email"])
        
        # Write Email to Column 5
        ws_firmas.append_row([today_iso, signature.tecnico_nombre, str(signature.timestamp), signature.signature_ref, user_email or "", "PENDIENTE"])
        print(f"DEBUG [SHEETS] Signature appended to '{firmas_title}' with email '{user_email}'")

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

def sync_expense_to_sheet(expense, tech_name, section=None):
    """Appends an expense row to the 'Gastos' sheet."""
    print(f"\n>>> [SHEETS START] Syncing expense {expense.concept}...")
    try:
        sheet = get_sheet()
        if not sheet: return

        try:
            ws = sheet.worksheet("Gastos")
        except gspread.WorksheetNotFound:
            ws = sheet.add_worksheet(title="Gastos", rows=1000, cols=8)
            ws.append_row(["Fecha", "Concepto", "Sección", "Categoría", "Monto", "Método Pago", "Usuario", "Imagen URL"])

        new_row = [
            str(expense.date),
            expense.concept,
            section or "OTROS",
            expense.category,
            expense.amount,
            expense.payment_method or "N/A",
            tech_name,
            expense.image_url or ""
        ]
        ws.append_row(new_row)
        print(f"DEBUG [SHEETS] Expense appended to 'Gastos'.")
    except Exception as e:
        print(f"ERROR [SHEETS] Expense sync failed: {e}")

def get_dashboard_data(tech_name: str):
    """
    Retrieves balance, budget, and category spending from 'Config', 'Presupuesto' and 'Gastos' sheets.
    """
    try:
        sheet = get_sheet()
        if not sheet: return None

        # 1. Get Config (Name, Global Budget)
        config = {"name": "Usuario", "monthly_budget": 0}
        try:
            ws_config = sheet.worksheet("Config")
            data = ws_config.get_all_records()
            for row in data:
                key = str(row.get("Key", "")).lower()
                if "nombre" in key or "name" in key: config["name"] = row.get("Value", "Carlos")
                if "presupuesto" in key or "budget" in key: config["monthly_budget"] = int(row.get("Value", 0))
        except: pass

        # 2. Get Budgets per Section (Hierarchical)
        sections = {}
        # category_to_section is useful for mapping expenses that only have category
        category_to_section = {}
        try:
            ws_budget = sheet.worksheet("Presupuesto")
            data = ws_budget.get_all_records()
            for row in data:
                sec = str(row.get("Sección") or "OTROS").strip()
                cat = str(row.get("Categoría") or row.get("Category") or "General").strip()
                bud = int(row.get("Presupuesto") or row.get("Budget") or 0)
                
                category_to_section[cat] = sec
                
                if sec not in sections:
                    sections[sec] = {"budget": 0, "spent": 0, "categories": {}}
                
                sections[sec]["budget"] += bud
                sections[sec]["categories"][cat] = {"budget": bud, "spent": 0}
        except: pass

        # 3. Calculate Spent per Category/Section (current month)
        try:
            ws_gastos = sheet.worksheet("Gastos")
            data = ws_gastos.get_all_records()
            from datetime import date
            current_month = date.today().month
            current_year = date.today().year
            
            total_spent = 0
            for row in data:
                try:
                    fecha_str = str(row.get("Fecha", ""))
                    from datetime import datetime
                    d = None
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                        try: d = datetime.strptime(fecha_str, fmt); break
                        except: continue
                    
                    if d and d.month == current_month and d.year == current_year:
                        sec = str(row.get("Sección", "")).strip()
                        cat = str(row.get("Categoría") or row.get("Category", "")).strip()
                        monto = int(row.get("Monto") or row.get("Amount") or 0)
                        
                        total_spent += monto
                        
                        # Use section from row if available, else map from category
                        if not sec and cat in category_to_section:
                            sec = category_to_section[cat]
                        
                        if not sec: sec = "OTROS"
                        
                        if sec not in sections:
                            sections[sec] = {"budget": 0, "spent": 0, "categories": {}}
                        
                        sections[sec]["spent"] += monto
                        if cat:
                            if cat not in sections[sec]["categories"]:
                                sections[sec]["categories"][cat] = {"budget": 0, "spent": 0}
                            sections[sec]["categories"][cat]["spent"] += monto
                except: continue
        except: pass

        return {
            "user_name": config["name"],
            "available_balance": config["monthly_budget"] - total_spent,
            "monthly_budget": config["monthly_budget"],
            "categories": sections, # Frontend will now receive sections as the top-level
            "total_spent": total_spent
        }
    except Exception as e:
        print(f"ERROR [SHEETS] get_dashboard_data failed: {e}")
        return None


def get_technician_scores(tech_name: str):
    """
    Retrieves score data for a specific technician from 'Puntajes' sheet.
    Returns: dict with totals and history.
    """
    print(f"DEBUG [SHEETS] Fetching scores for: {tech_name}")
    try:
        sheet = get_sheet()
        if not sheet: return None
        
        try:
            ws = sheet.worksheet("Puntajes")
        except:
            print("DEBUG [SHEETS] 'Puntajes' sheet not found.")
            return None
            
        all_rows = ws.get_all_values()
        if not all_rows: return None
        
        headers = [h.strip().lower() for h in all_rows[0]]
        try:
            idx_tech = headers.index("técnico")
            idx_date = headers.index("fecha")
            idx_ticket = headers.index("ticket id")
            idx_points = headers.index("puntos finales")
            idx_money = headers.index("dinero")
            idx_items = headers.index("items detectados")
        except ValueError as e:
            print(f"DEBUG [SHEETS] Missing headers in Puntajes: {e}")
            return None
            
        history = []
        total_points = 0.0
        total_money = 0
        
        target_tech = tech_name.strip().lower()
        
        # Parse rows
        for row in all_rows[1:]:
            if len(row) <= idx_money: continue
            
            row_tech = row[idx_tech].strip().lower()
            
            # Loose match or exact? Usually exact from Bitacora logic.
            if target_tech in row_tech or row_tech in target_tech:
                try:
                    pts = float(row[idx_points].replace(',', '.'))
                    money = int(float(row[idx_money].replace(',', '.'))) # simple cast
                    
                    total_points += pts
                    total_money += money
                    
                    history.append({
                        "date": row[idx_date],
                        "ticket_id": row[idx_ticket],
                        "points": pts,
                        "money": money,
                        "items": row[idx_items]
                    })
                except Exception as e:
                    print(f"DEBUG [SHEETS] Parse error row: {e}")
                    continue

        # Sort history by date desc?
        # Date format in sheet is likely YYYY-MM-DD from update_puntajes logic
        history.sort(key=lambda x: x["date"], reverse=True)

        return {
            "technician": tech_name,
            "total_points": round(total_points, 2),
            "total_money": total_money,
            "history": history
        }

    except Exception as e:
        print(f"ERROR [SHEETS] Get scores failed: {e}")
        return None

def add_category_to_sheet(section: str, category: str, budget: int = 0):
    """
    Adds a new category (subcategory) to the 'Presupuesto' sheet.
    """
    print(f"DEBUG [SHEETS] Adding category '{category}' to section '{section}'")
    try:
        sheet = get_sheet()
        if not sheet: return False
        
        try:
            ws = sheet.worksheet("Presupuesto")
        except gspread.WorksheetNotFound:
            ws = sheet.add_worksheet(title="Presupuesto", rows=100, cols=3)
            ws.append_row(["Sección", "Categoría", "Presupuesto"])

        # Check for duplicates?
        # Ideally yes, but for MVP let's just append.
        # Structure: Sección, Categoría, Presupuesto
        ws.append_row([section, category, budget])
        return True
    except Exception as e:
        print(f"ERROR [SHEETS] Add category failed: {e}")
        return False

def delete_category_from_sheet(section: str, category: str):
    """
    Deletes a category from the 'Presupuesto' sheet.
    """
    print(f"DEBUG [SHEETS] Deleting category '{category}' from section '{section}'")
    try:
        sheet = get_sheet()
        if not sheet: return False
        
        try:
            ws = sheet.worksheet("Presupuesto")
        except:
            return False

        all_rows = ws.get_all_values()
        if not all_rows: return False
        
        headers = [h.strip().lower() for h in all_rows[0]]
        try:
            sec_col = -1
            cat_col = -1
            for c in ["sección", "seccion", "section"]:
                if c in headers: sec_col = headers.index(c); break
                
            for c in ["categoría", "categoria", "category"]:
                if c in headers: cat_col = headers.index(c); break
                
            if sec_col == -1 or cat_col == -1:
                return False
                
            # Find row to delete
            # Start from 2 (index 1 in 0-based list is row 2)
            for i, row in enumerate(all_rows[1:], start=2):
                if len(row) > max(sec_col, cat_col):
                    r_sec = row[sec_col].strip()
                    r_cat = row[cat_col].strip()
                    if r_sec == section and r_cat == category:
                        ws.delete_rows(i)
                        print(f"DEBUG [SHEETS] Deleted row {i}")
                        return True
            
            return False # Not found
            
        except Exception as e:
            print(f"ERROR [SHEETS] Delete finding row failed: {e}")
            return False

    except Exception as e:
        print(f"ERROR [SHEETS] Delete category failed: {e}")
        return False

def update_category_in_sheet(section: str, category: str, new_budget: int):
    """
    Updates a category's budget in the 'Presupuesto' sheet.
    """
    print(f"DEBUG [SHEETS] Updating category '{category}' budget to {new_budget}")
    try:
        sheet = get_sheet()
        if not sheet: return False
        
        ws = sheet.worksheet("Presupuesto")
        all_rows = ws.get_all_values()
        if not all_rows: return False
        
        headers = [h.strip().lower() for h in all_rows[0]]
        sec_col = -1
        cat_col = -1
        bud_col = -1
        
        for c in ["sección", "seccion", "section"]:
            if c in headers: sec_col = headers.index(c); break
        for c in ["categoría", "categoria", "category"]:
            if c in headers: cat_col = headers.index(c); break
        for c in ["presupuesto", "budget"]:
            if c in headers: bud_col = headers.index(c); break
            
        if sec_col == -1 or cat_col == -1 or bud_col == -1:
            return False
            
        for i, row in enumerate(all_rows[1:], start=2):
            if len(row) > max(sec_col, cat_col):
                if row[sec_col].strip() == section and row[cat_col].strip() == category:
                    ws.update_cell(i, bud_col + 1, new_budget)
                    return True
        return False
    except Exception as e:
        print(f"ERROR [SHEETS] Update category failed: {e}")
        return False

def sync_commitment_to_sheet(commitment, user_name="Carlos"):
    """
    Syncs a commitment to 'Compromisos' sheet (Append or Update).
    """
    print(f"DEBUG [SHEETS] Syncing commitment {commitment.id} - {commitment.title}")
    try:
        sheet = get_sheet()
        if not sheet: return

        try:
            ws = sheet.worksheet("Compromisos")
        except gspread.WorksheetNotFound:
            ws = sheet.add_worksheet(title="Compromisos", rows=1000, cols=9)
            ws.append_row(["ID", "Fecha Creación", "Título", "Tipo", "Monto Total", "Monto Pagado", "Vencimiento", "Estado", "Usuario"])

        # Prepare row data
        # ID, Created, Title, Type, Total, Paid, Due, Status, User
        row_data = [
            str(commitment.id),
            str(commitment.created_at.date()) if commitment.created_at else "",
            commitment.title,
            commitment.type, # DEBT / LOAN
            commitment.total_amount,
            commitment.paid_amount,
            str(commitment.due_date) if commitment.due_date else "",
            commitment.status,
            user_name
        ]

        # Find if ID exists (Column 1)
        found_cell = None
        try:
            found_cell = ws.find(str(commitment.id), in_column=1)
        except:
            pass

        if found_cell:
            # Update existing row
            # gspread's update method: ws.update(range_name, values=List[List])
            # Row index is found_cell.row
            # We want to update columns A to I (1 to 9)
            cell_range = f"A{found_cell.row}:I{found_cell.row}"
            ws.update(cell_range, [row_data])
            print(f"DEBUG [SHEETS] Updated existing commitment row {found_cell.row}")
        else:
            # Append
            ws.append_row(row_data)
            print(f"DEBUG [SHEETS] Appended new commitment.")

    except Exception as e:
        print(f"ERROR [SHEETS] Commitment sync failed: {e}")

def delete_commitment_from_sheet(commitment_id: int):
    """
    Deletes a commitment row from sheet by ID.
    """
    print(f"DEBUG [SHEETS] Deleting commitment {commitment_id}")
    try:
        sheet = get_sheet()
        if not sheet: return

        try:
            ws = sheet.worksheet("Compromisos")
        except:
            return

        try:
            found_cell = ws.find(str(commitment_id), in_column=1)
            if found_cell:
                ws.delete_rows(found_cell.row)
                print(f"DEBUG [SHEETS] Deleted commitment row {found_cell.row}")
        except:
            print("DEBUG [SHEETS] Commitment ID not found for deletion.")
            pass

    except Exception as e:
        print(f"ERROR [SHEETS] Delete commitment failed: {e}")
