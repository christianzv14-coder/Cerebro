import pandas as pd
from typing import IO
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import Activity, ActivityState, User, Role
from app.core.security import get_password_hash

REQUIRED_COLUMNS = ['fecha', 'ticket_id', 'tecnico_nombre', 'patente', 'cliente', 'direccion', 'tipo_trabajo']

def process_excel_upload(file: IO, db: Session):
    with open("upload_debug.log", "a") as f:
        f.write(f"\n\n--- UPLOAD STARTED AT {datetime.now()} ---\n")

    try:
        df = pd.read_excel(file)
        with open("upload_debug.log", "a") as f:
            f.write(f"DataFrame Shape: {df.shape} (Rows, Cols)\n")
    except Exception as e:
        with open("upload_debug.log", "a") as f:
            f.write(f"ERROR reading excel: {e}\n")
        raise ValueError(f"Error reading Excel file: {e}")

    # Validate columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
         raise ValueError(f"Missing required columns: {missing_cols}")

    processed_count = 0
    created_count = 0
    updated_count = 0
    
    # --- STRATEGY: Smart Retry & Update (Refined) ---
    
    # 1. Gather Excel Ticket IDs
    excel_ticket_ids = []
    if 'ticket_id' in df.columns:
        excel_ticket_ids = [str(x).strip() for x in df['ticket_id'].dropna().unique()]
    
    if not excel_ticket_ids:
        return {"processed": 0, "created": 0, "updated": 0}

    # 2. Analyze Existing DB Records (Capture Tech!)
    existing_activities = db.query(Activity).filter(Activity.ticket_id.in_(excel_ticket_ids)).all()
    db_map = {act.ticket_id: act for act in existing_activities}

    # 3. Determine Actions per Ticket
    ids_to_delete = []
    retry_map = {} # { "TICKET-123": "TICKET-123-R1" }
    backup_map = {} 

    for index, row in df.iterrows():
        if pd.isna(row['ticket_id']): continue
        tid = str(row['ticket_id']).strip()
        
        # Get Excel Tech Name
        raw_tech = row['tecnico_nombre'] if pd.notna(row['tecnico_nombre']) else "Sin Asignar"
        excel_tech = str(raw_tech).strip() # Keep case for fuzzy match later, but generic usage here

        if tid in db_map:
            db_act = db_map[tid]
            db_tech = str(db_act.tecnico_nombre).strip()
            # Strict Closed Check
            is_closed = db_act.estado in [ActivityState.FALLIDO, ActivityState.EXITOSO, ActivityState.REPROGRAMADO]
            
            # Helper to normalize for comparison
            def norm(s): return str(s).strip().lower().replace("  ", " ")
            tech_differs = norm(excel_tech) != norm(db_tech)

            # CONDITION A: Tech Changed AND Task was Closed -> RETRY (Split)
            if tech_differs and is_closed:
                # We do NOT delete the old one. We map a new ID.
                retry_map[tid] = tid + "-REINTENTO" # Simple suffix
                with open("upload_debug.log", "a") as f:
                    f.write(f"DETECTED RETRY: {tid} ({db_tech}->{excel_tech}). Suffixing.\n")
                
            # CONDITION B: Update (Delete & Restore)
            else:
                ids_to_delete.append(tid)
                backup_map[tid] = {
                    "estado": db_act.estado,
                    "resultado_motivo": db_act.resultado_motivo,
                    "observacion": db_act.observacion,
                    "hora_inicio": db_act.hora_inicio,
                    "hora_fin": db_act.hora_fin,
                    "tecnico_original": db_act.tecnico_nombre  # CRITICAL: Save this
                }

    # 4. Delete Records to be Overwritten
    if ids_to_delete:
        try:
            db.query(Activity).filter(Activity.ticket_id.in_(ids_to_delete)).delete(synchronize_session=False)
            db.commit()
        except Exception as e:
            db.rollback()
            raise ValueError(f"Failed to clear rows: {e}")

    # 5. Iterate & Create
    for index, row in df.iterrows():
        if pd.isna(row['ticket_id']): continue
        
        original_tid = str(row['ticket_id']).strip()
        final_ticket_id = original_tid
        
        # Are we creating a Retried Task?
        is_retry = False
        if original_tid in retry_map:
            final_ticket_id = retry_map[original_tid]
            is_retry = True
            
        # Resolved Tech Name
        raw_tech = row['tecnico_nombre']
        if pd.isna(raw_tech) or str(raw_tech).strip() == "" or str(raw_tech).lower() == "nan":
            tecnico_nombre = "Sin Asignar"
        else:
            tecnico_nombre = str(raw_tech).strip()
            
        fecha_val = pd.to_datetime(row['fecha']).date()
        if pd.isna(fecha_val):
            from datetime import date
            fecha_val = date.today()

        # User Provisioning (Compact)
        import unicodedata, difflib
        def normalize_str(s): return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8').lower()
        all_users = db.query(User).all()
        user_map = {normalize_str(u.tecnico_nombre): u for u in all_users}
        clean_input = normalize_str(tecnico_nombre)
        user = user_map.get(clean_input)
        if not user:
             matches = difflib.get_close_matches(clean_input, list(user_map.keys()), n=1, cutoff=0.75)
             if matches:
                 user = user_map[matches[0]]
                 tecnico_nombre = user.tecnico_nombre
        if not user:
            clean_tech_name = tecnico_nombre.replace(" ", "_").lower()
            new_user = User(email=f"{clean_tech_name}@cerebro.com", tecnico_nombre=tecnico_nombre, hashed_password=get_password_hash("123456"), role=Role.TECH)
            if db.query(User).filter(User.email == new_user.email).first(): new_user.email = f"{new_user.email}_dup_{index}"
            db.add(new_user); db.commit(); db.refresh(new_user); tecnico_nombre = new_user.tecnico_nombre
        else:
            tecnico_nombre = user.tecnico_nombre

        # STATE RESTORATION LOGIC
        restored_state = ActivityState.PENDIENTE
        restored_motivo = None
        restored_obs = None
        restored_start = None
        restored_end = None
        
        if is_retry:
             # Case: Tech Changed on Closed Task -> FORCE NEW
             restored_state = ActivityState.PENDIENTE
             created_count += 1
             
        elif original_tid in backup_map:
             # Case: Update on existing task.
             # CHECK: Did tech change locally? (e.g. Activity was 'Simulado' but Tech changed in Excel)
             # If exact same Tech -> Restore everything.
             # If different Tech -> Force PENDIENTE (User Intent: Re-assign)
             
             b = backup_map[original_tid]
             old_tech_b = str(b.get("tecnico_original", "")).strip()
             new_tech_b = str(tecnico_nombre).strip()
             
             if normalize_str(old_tech_b) != normalize_str(new_tech_b):
                 # Tech Changed in an "Update" scenario (e.g. task was Pending/Simulado but re-assigned)
                 restored_state = ActivityState.PENDIENTE
                 # Drop motive/obs? Usually yes if new tech.
                 created_count += 1 # Effectively a 'new' assignment
             else:
                 # Same Tech -> Restore status (Address Correction etc)
                 restored_state = b["estado"]
                 restored_motivo = b["resultado_motivo"]
                 restored_obs = b["observacion"]
                 restored_start = b["hora_inicio"]
                 restored_end = b["hora_fin"]
                 updated_count += 1
        else:
             # Entirely New
             created_count += 1

        new_act = Activity(
            ticket_id=final_ticket_id,
            fecha=fecha_val,
            tecnico_nombre=tecnico_nombre, 
            patente=str(row['patente']) if pd.notna(row['patente']) else None,
            cliente=str(row['cliente']) if pd.notna(row['cliente']) else None,
            direccion=str(row['direccion']) if pd.notna(row['direccion']) else None,
            tipo_trabajo=str(row['tipo_trabajo']) if pd.notna(row['tipo_trabajo']) else None,
            prioridad=str(row['Prioridad']) if 'Prioridad' in df.columns and pd.notna(row['Prioridad']) else None,
            accesorios=str(row['Accesorios']) if 'Accesorios' in df.columns and pd.notna(row['Accesorios']) else None,
            comuna=str(row['Comuna']) if 'Comuna' in df.columns and pd.notna(row['Comuna']) else None,
            region=str(row['Region']) if 'Region' in df.columns and pd.notna(row['Region']) else None,
            
            estado=restored_state,
            resultado_motivo=restored_motivo,
            observacion=restored_obs,
            hora_inicio=restored_start,
            hora_fin=restored_end
        )
        db.add(new_act)
        processed_count += 1
        
        try:
             from app.services.sheets_service import sync_activity_to_sheet
             sync_activity_to_sheet(new_act)
        except Exception: pass
        
        if index % 50 == 0: db.commit()
            
    db.commit()
    
    stats = {"processed": processed_count, "created": created_count, "updated": updated_count}

    # Send Email Summary (Also Try Server Side)
    try:
        from app.services.email_service import send_plan_summary
        send_plan_summary(stats, df)
    except Exception as e:
        print(f"DEBUG: Failed to trigger email summary: {e}")
    
    return stats
