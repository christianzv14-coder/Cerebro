import pandas as pd
from typing import IO
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import Activity, ActivityState, User, Role
from app.core.security import get_password_hash

REQUIRED_COLUMNS = ['fecha', 'ticket_id', 'tecnico_nombre', 'patente', 'cliente', 'direccion', 'tipo_trabajo']

def process_excel_upload(file: IO, db: Session):
    try:
        df = pd.read_excel(file)
    except Exception as e:
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
            db.query(Activity).filter(
                Activity.fecha == d,
                Activity.tecnico_nombre == tech,
                Activity.estado == ActivityState.PENDIENTE
            ).delete()
        db.commit()
    except Exception as e:
        print(f"DEBUG [EXCEL] Pre-cleaning failed: {e}")
        db.rollback()

    for index, row in df.iterrows():
        # Validate row data
        if pd.isna(row['ticket_id']) or pd.isna(row['tecnico_nombre']):
             continue # Skip empty rows

        ticket_id = str(row['ticket_id']).strip()
        tecnico_nombre = str(row['tecnico_nombre']).strip()
        fecha_val = pd.to_datetime(row['fecha']).date()
        
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
                updated_count += 1
                
            # Case 3: NOT PENDIENTE -> Safe Update Only
            else:
                # Only update info fields, NOT criticals (tecnico, fecha)
                activity.patente = str(row['patente']) if pd.notna(row['patente']) else activity.patente
                activity.cliente = str(row['cliente']) if pd.notna(row['cliente']) else activity.cliente
                activity.direccion = str(row['direccion']) if pd.notna(row['direccion']) else activity.direccion
                activity.tipo_trabajo = str(row['tipo_trabajo']) if pd.notna(row['tipo_trabajo']) else activity.tipo_trabajo
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
    
    return {
        "processed": processed_count,
        "created": created_count,
        "updated": updated_count
    }
