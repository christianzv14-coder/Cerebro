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
            f.write(f"Columns found: {list(df.columns)}\n")
            f.write(f"First row: {df.iloc[0].to_dict() if not df.empty else 'EMPTY'}\n")
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
                Activity.tecnico_nombre == tech
            ).delete()
            
            # Also reset Signature for this day/tech if exists, ensuring "Sign" button resets
            deleted_sigs = db.query(DaySignature).filter(
                DaySignature.fecha == d,
                DaySignature.tecnico_nombre == tech
            ).delete()
            
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
        
        # Ensure User exists (Auto-provisioning for MVP)
        user = db.query(User).filter(User.tecnico_nombre == tecnico_nombre).first()
        if not user:
            # Create dummy user to satisfy FK
            # Password default: "123456" for new techs
            new_user = User(
                email=f"{tecnico_nombre.replace(' ', '.').lower()}@cerebro.com", # Mock email
                tecnico_nombre=tecnico_nombre,
                hashed_password=get_password_hash("123456"),
                role=Role.TECH
            )
            # Handle potential email collision if name logic produces same email? Unlikely for MVP.
            # But better verify email unique.
            if db.query(User).filter(User.email == new_user.email).first():
                 new_user.email = f"{new_user.email}_dup_{index}" 
                 
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

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

    # Send Email Summary (DISABLED due to Railway Port Blocking)
    # try:
    #     from app.services.email_service import send_plan_summary
    #     # Pass stats and the ORIGINAL DataFrame (df) to calculate breakdowns
    #     send_plan_summary(stats, df)
    # except Exception as e:
    #     print(f"DEBUG: Failed to trigger email summary: {e}")
    
    return stats
