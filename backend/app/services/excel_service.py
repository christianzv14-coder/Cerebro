import pandas as pd
from typing import IO
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import Activity, ActivityState, User, Role, DaySignature
from app.core.security import get_password_hash

REQUIRED_COLUMNS = ['fecha', 'ticket_id', 'tecnico_nombre', 'patente', 'cliente', 'direccion', 'tipo_trabajo']

def process_excel_upload(file: IO, db: Session):
    with open("upload_debug.log", "a") as f:
        f.write(f"\n\n--- UPLOAD STARTED AT {datetime.now()} ---\n")

    try:
        df = pd.read_excel(file)
        with open("upload_debug.log", "a") as f:
            f.write(f"DataFrame Shape: {df.shape} (Rows, Cols)\n")
            f.write(f"Columns found: {list(df.columns)}\n")
            f.write(f"First row: {df.iloc[0].to_dict() if not df.empty else 'EMPTY'}\n")
            # Log all Ticket IDs to see what we got
            if 'ticket_id' in df.columns:
                 f.write(f"Ticket IDs in file: {df['ticket_id'].tolist()}\n")
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
    
    # Pre-clean logic: Delete existing PENDIENTE activities for the techs and dates in the Excel
    # to ensure the app view matches the Excel exactly as requested.
    try:
        # Collect unique pairs of (date, tecnico_nombre)
        unique_pairs = set()
        for index, row in df.iterrows():
            if pd.notna(row['ticket_id']) and pd.notna(row['tecnico_nombre']):
                d = pd.to_datetime(row['fecha']).date()
                unique_pairs.add((d, str(row['tecnico_nombre']).strip()))
        
        for d, tech in unique_pairs:
            with open("upload_debug.log", "a") as f:
                f.write(f"Pre-cleaning for Tech: '{tech}', Date: '{d}'\n")
            
            deleted_acts = db.query(Activity).filter(
                Activity.fecha == d,
                Activity.tecnico_nombre == tech,
                Activity.estado == ActivityState.PENDIENTE # FIX: Only delete PENDIENTE, preserve history
            ).delete()
            
            # FIX: Do NOT delete signatures. If they signed, they signed.
            # deleted_sigs = db.query(DaySignature)...
            
            with open("upload_debug.log", "a") as f:
                f.write(f"  -> Deleted {deleted_acts} activities, {deleted_sigs} signatures.\n")

        db.commit()
    except Exception as e:
        print(f"DEBUG [EXCEL] Pre-cleaning failed: {e}")
        with open("upload_debug.log", "a") as f:
            f.write(f"ERROR in Pre-cleaning: {e}\n")
        db.rollback()

    for index, row in df.iterrows():
        # Validate row data
        if pd.isna(row['ticket_id']):
             continue # Skip empty rows

        ticket_id = str(row['ticket_id']).strip()
        
        # Handle empty/NaN technician (Mantis default)
        raw_tech = row['tecnico_nombre']
        if pd.isna(raw_tech) or str(raw_tech).strip() == "" or str(raw_tech).lower() == "nan":
            tecnico_nombre = "Sin Asignar"
        else:
            tecnico_nombre = str(raw_tech).strip()
            
        fecha_val = pd.to_datetime(row['fecha']).date()
        if pd.isna(fecha_val):
            # Default to today if missing? Or keep going
            from datetime import date
            fecha_val = date.today()
        
        # Ensure User exists (Auto-provisioning with FUZZY MATCH)
        # 1. Prepare DB User Map (Normalized keys for fast lookup)
        all_users = db.query(User).all()
        
        import unicodedata
        import difflib
        
        def normalize_str(s):
            return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8').lower()
            
        user_map = {normalize_str(u.tecnico_nombre): u for u in all_users}
        known_names_normalized = list(user_map.keys())
        
        clean_input = normalize_str(tecnico_nombre)
        
        # 2. Try Exact Normalized Match
        user = user_map.get(clean_input)
        
        # 3. Fuzzy Match (If exact fails)
        if not user:
            # cutoff=0.8 means 80% similarity required. "Parez" vs "Perez" is >80%.
            matches = difflib.get_close_matches(clean_input, known_names_normalized, n=1, cutoff=0.75)
            if matches:
                best_match_key = matches[0]
                user = user_map[best_match_key]
                print(f"DEBUG [EXCEL]: Fuzzy Match! Input '{tecnico_nombre}' -> DB '{user.tecnico_nombre}'")
                tecnico_nombre = user.tecnico_nombre # AUTO-CORRECT the name to match DB
                
        # 4. Create New User (If really no match)
        if not user:
            print(f"DEBUG [EXCEL]: No match for '{tecnico_nombre}'. creating new user.")
            clean_tech_name = tecnico_nombre.replace(" ", "_").lower()
            new_user = User(
                email=f"{clean_tech_name}@cerebro.com", # Mock email
                tecnico_nombre=tecnico_nombre,
                hashed_password=get_password_hash("123456"),
                role=Role.TECH
            )
            # Handle potential email collision
            if db.query(User).filter(User.email == new_user.email).first():
                 new_user.email = f"{new_user.email}_dup_{index}" 
                 
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            tecnico_nombre = new_user.tecnico_nombre
        else:
            # We found the user (Exact or Fuzzy), ensure we use their OFFICIAL name
            tecnico_nombre = user.tecnico_nombre

        # Merge Logic
        activity = db.query(Activity).filter(Activity.ticket_id == ticket_id).first()
        
        if not activity:
            # CREATE
            new_act = Activity(
                ticket_id=ticket_id,
                fecha=fecha_val,
                tecnico_nombre=tecnico_nombre,
                patente=str(row['patente']) if pd.notna(row['patente']) else None,
                cliente=str(row['cliente']) if pd.notna(row['cliente']) else None,
                direccion=str(row['direccion']) if pd.notna(row['direccion']) else None,
                tipo_trabajo=str(row['tipo_trabajo']) if pd.notna(row['tipo_trabajo']) else None,
                
                # New fields - Handle missing columns gracefully
                prioridad=str(row['Prioridad']) if 'Prioridad' in df.columns and pd.notna(row['Prioridad']) else None,
                accesorios=str(row['Accesorios']) if 'Accesorios' in df.columns and pd.notna(row['Accesorios']) else None,
                comuna=str(row['Comuna']) if 'Comuna' in df.columns and pd.notna(row['Comuna']) else None,
                region=str(row['Region']) if 'Region' in df.columns and pd.notna(row['Region']) else None,
                
                estado=ActivityState.PENDIENTE
            )
            db.add(new_act)
            created_count += 1
        else:
            # UPDATE
            # Case 2: PENDIENTE -> Full Update
            if activity.estado == ActivityState.PENDIENTE:
                activity.fecha = fecha_val
                activity.tecnico_nombre = tecnico_nombre # Allow reassign
                activity.patente = str(row['patente']) if pd.notna(row['patente']) else None
                activity.cliente = str(row['cliente']) if pd.notna(row['cliente']) else None
                activity.direccion = str(row['direccion']) if pd.notna(row['direccion']) else None
                activity.tipo_trabajo = str(row['tipo_trabajo']) if pd.notna(row['tipo_trabajo']) else None
                
                # New fields
                activity.prioridad = str(row['Prioridad']) if 'Prioridad' in df.columns and pd.notna(row['Prioridad']) else None
                activity.accesorios = str(row['Accesorios']) if 'Accesorios' in df.columns and pd.notna(row['Accesorios']) else None
                activity.comuna = str(row['Comuna']) if 'Comuna' in df.columns and pd.notna(row['Comuna']) else None
                activity.region = str(row['Region']) if 'Region' in df.columns and pd.notna(row['Region']) else None
                updated_count += 1
                
            # Case 3: NOT PENDIENTE -> Safe Update Only
            else:
                # Only update info fields, NOT criticals (tecnico, fecha)
                activity.patente = str(row['patente']) if pd.notna(row['patente']) else activity.patente
                activity.cliente = str(row['cliente']) if pd.notna(row['cliente']) else activity.cliente
                activity.direccion = str(row['direccion']) if pd.notna(row['direccion']) else activity.direccion
                activity.tipo_trabajo = str(row['tipo_trabajo']) if pd.notna(row['tipo_trabajo']) else activity.tipo_trabajo
                
                # Update new fields
                activity.prioridad = str(row['Prioridad']) if 'Prioridad' in df.columns and pd.notna(row['Prioridad']) else activity.prioridad
                activity.accesorios = str(row['Accesorios']) if 'Accesorios' in df.columns and pd.notna(row['Accesorios']) else activity.accesorios
                activity.comuna = str(row['Comuna']) if 'Comuna' in df.columns and pd.notna(row['Comuna']) else activity.comuna
                activity.region = str(row['Region']) if 'Region' in df.columns and pd.notna(row['Region']) else activity.region
                # IGNORE: fecha, tecnico_nombre
                updated_count += 1
        
        processed_count += 1
        
        # Sync to Sheets (Planning Phase)
        try:
            from app.services.sheets_service import sync_activity_to_sheet
            sync_activity_to_sheet(activity if activity else new_act)
        except Exception as e:
            print(f"DEBUG [EXCEL] Sheet sync failed for ticket {ticket_id}: {e}")
            
        # Periodic flush?
        if index % 50 == 0:
            db.commit()
            
    db.commit()
    
    stats = {
        "processed": processed_count,
        "created": created_count,
        "updated": updated_count
    }

    # Send Email Summary
    try:
        with open("upload_debug.log", "a") as f:
            f.write("Attempting to import email_service...\n")
            
        from app.services.email_service import send_plan_summary
        
        with open("upload_debug.log", "a") as f:
            f.write("Calling send_plan_summary...\n")
            
        # Pass stats and the ORIGINAL DataFrame (df) to calculate breakdowns
        send_plan_summary(stats, df)
        
        with open("upload_debug.log", "a") as f:
            f.write("Returned from send_plan_summary.\n")
            
    except Exception as e:
        with open("upload_debug.log", "a") as f:
            f.write(f"DEBUG: Failed to trigger email summary: {e}\n")
        print(f"DEBUG: Failed to trigger email summary: {e}")
    
    return stats
