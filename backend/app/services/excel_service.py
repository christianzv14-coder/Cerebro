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
            if 'ticket_id' in df.columns:
                 f.write(f"Ticket IDs: {df['ticket_id'].tolist()}\n")
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
    
    # --- NEW STRATEGY: Backup -> Delete -> Create -> Restore ---
    # Goal: Excel is master for Metadata. DB is master for Status.
    
    # 1. Gather all Ticket IDs from Excel
    excel_ticket_ids = []
    if 'ticket_id' in df.columns:
        excel_ticket_ids = [str(x).strip() for x in df['ticket_id'].dropna().unique()]
    
    if not excel_ticket_ids:
        return {"processed": 0, "created": 0, "updated": 0}

    # 2. Backup Status/History for THESE tickets
    existing_activities = db.query(Activity).filter(Activity.ticket_id.in_(excel_ticket_ids)).all()
    
    backup_map = {}
    for act in existing_activities:
        backup_map[act.ticket_id] = {
            "estado": act.estado,
            "resultado_motivo": act.resultado_motivo,
            "observacion": act.observacion,
            "hora_inicio": act.hora_inicio,
            "hora_fin": act.hora_fin
        }
        
    with open("upload_debug.log", "a") as f:
        f.write(f"Backed up status for {len(backup_map)} tickets.\n")

    # 3. Aggressive Delete by TICKET ID
    try:
        deleted_count = db.query(Activity).filter(Activity.ticket_id.in_(excel_ticket_ids)).delete(synchronize_session=False)
        db.commit()
        with open("upload_debug.log", "a") as f:
            f.write(f"Aggressively deleted {deleted_count} rows.\n")
    except Exception as e:
        db.rollback()
        raise ValueError(f"Failed to clear rows: {e}")

    # 4. Iterate & Create (Restoring Status)
    for index, row in df.iterrows():
        if pd.isna(row['ticket_id']): continue

        ticket_id = str(row['ticket_id']).strip()
        
        # Tech Logic
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
            # Create new
            clean_tech_name = tecnico_nombre.replace(" ", "_").lower()
            new_user = User(email=f"{clean_tech_name}@cerebro.com", tecnico_nombre=tecnico_nombre, hashed_password=get_password_hash("123456"), role=Role.TECH)
            if db.query(User).filter(User.email == new_user.email).first(): new_user.email = f"{new_user.email}_dup_{index}"
            db.add(new_user); db.commit(); db.refresh(new_user); tecnico_nombre = new_user.tecnico_nombre
        else:
            tecnico_nombre = user.tecnico_nombre
            
        # RESTORE STATE
        restored_state = ActivityState.PENDIENTE
        restored_motivo = None
        restored_obs = None
        restored_start = None
        restored_end = None
        
        if ticket_id in backup_map:
            b = backup_map[ticket_id]
            restored_state = b["estado"]
            restored_motivo = b["resultado_motivo"]
            restored_obs = b["observacion"]
            restored_start = b["hora_inicio"]
            restored_end = b["hora_fin"]
            updated_count += 1
        else:
            created_count += 1

        new_act = Activity(
            ticket_id=ticket_id,
            fecha=fecha_val,
            tecnico_nombre=tecnico_nombre, # EXCEL WINS
            patente=str(row['patente']) if pd.notna(row['patente']) else None,
            cliente=str(row['cliente']) if pd.notna(row['cliente']) else None,
            direccion=str(row['direccion']) if pd.notna(row['direccion']) else None,
            tipo_trabajo=str(row['tipo_trabajo']) if pd.notna(row['tipo_trabajo']) else None,
            
            prioridad=str(row['Prioridad']) if 'Prioridad' in df.columns and pd.notna(row['Prioridad']) else None,
            accesorios=str(row['Accesorios']) if 'Accesorios' in df.columns and pd.notna(row['Accesorios']) else None,
            comuna=str(row['Comuna']) if 'Comuna' in df.columns and pd.notna(row['Comuna']) else None,
            region=str(row['Region']) if 'Region' in df.columns and pd.notna(row['Region']) else None,
            
            # RESTORED VALUES
            estado=restored_state,
            resultado_motivo=restored_motivo,
            observacion=restored_obs,
            hora_inicio=restored_start,
            hora_fin=restored_end
        )
        db.add(new_act)
        processed_count += 1
        
        # Sheet Sync
        try:
             from app.services.sheets_service import sync_activity_to_sheet
             sync_activity_to_sheet(new_act)
        except Exception: pass
        
        if index % 50 == 0: db.commit()
            
    db.commit()
    
    stats = {
        "processed": processed_count,
        "created": created_count,
        "updated": updated_count
    }

    # Send Email Summary
    try:
        from app.services.email_service import send_plan_summary
        send_plan_summary(stats, df)
    except Exception as e:
        print(f"DEBUG: Failed to trigger email summary: {e}")
    
    return stats
