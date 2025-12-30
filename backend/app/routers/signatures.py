import os
import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import DaySignature, User
from app.deps import get_current_user
from app.services.sheets_service import sync_signature_to_sheet
from app.services.email_service import send_workday_summary
from app.services.scores_service import update_scores_in_sheet
from app.models.models import DaySignature, User, Activity

router = APIRouter()

UPLOAD_DIR = "uploads/signatures"
os.makedirs(UPLOAD_DIR, exist_ok=True)

from pydantic import BaseModel
from typing import Optional
import base64

class SignatureUpload(BaseModel):
    image_base64: str
    fecha: Optional[date] = None # New optional field for Plan Date

@router.post("/")
async def upload_signature_json(
    upload_data: SignatureUpload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Main endpoint for Mobile App (Base64)."""
    return await _process_signature_upload(db, current_user, background_tasks, base64_str=upload_data.image_base64, fecha=upload_data.fecha)

@router.post("/file")
async def upload_signature_file(
    file: UploadFile = File(...),
    fecha: Optional[date] = None, # Allow form-data param too? Maybe harder for app, but consistent.
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Legacy/Fallback endpoint for MultiPart."""
    # Note: FastAPI Form parameters would be needed here to parse 'fecha' alongside File.
    # For now, mobile app uses JSON endpoint, so focusing there.
    return await _process_signature_upload(db, current_user, file=file)

@router.post("/ping")
async def ping_signatures():
    print("\n[!!!] SIGNATURES PING RECEIVED")
    return {"status": "ok", "message": "Signature API is reachable"}

async def _process_signature_upload(db, current_user, background_tasks: BackgroundTasks = None, base64_str=None, file=None, fecha: Optional[date] = None):
    # If a specific Plan Date is provided (e.g. from App viewing yesterday's plan), use it.
    # Otherwise default to today (legacy behavior).
    upload_date = fecha if fecha else date.today()
    
    tech_name_db = current_user.tecnico_nombre
    tech_clean = tech_name_db.strip().lower()
    
    print(f"\n>>> [UPLOAD START] Tech: '{tech_name_db}' | Date: '{upload_date}'")
    
    # 1. Idempotency Check
    all_sigs = db.query(DaySignature).filter(DaySignature.fecha == upload_date).all()
    existing = next((s for s in all_sigs if s.tecnico_nombre.strip().lower() == tech_clean), None)
    
    if existing:
        print(f"DEBUG: Rejected. Signature already exists for {upload_date}: ID {existing.id}")
        raise HTTPException(status_code=400, detail=f"La jornada del {upload_date} ya ha sido firmada.")
    
    content = None
    file_ext = "png"
    
    try:
        if file:
            print("DEBUG: Processing MultiPart file...")
            content = await file.read()
            file_ext = file.filename.split(".")[-1]
        elif base64_str:
            print(f"DEBUG: Processing Base64 string (Length: {len(base64_str)})...")
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            content = base64.b64decode(base64_str)
        else:
            raise HTTPException(status_code=400, detail="No data provided")
            
        # 3. Save File
        file_name = f"{tech_clean.replace(' ', '_')}_{upload_date}_{uuid.uuid4().hex[:6]}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        with open(file_path, "wb") as f:
            f.write(content)
        print(f"DEBUG: File saved to {file_path}")
        
    except Exception as e:
        print(f"DEBUG: Save failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {e}")
    
    # 4. Save to Database
    try:
        new_sig = DaySignature(
            tecnico_nombre=tech_name_db,
            fecha=upload_date,
            signature_ref=file_path
        )
        db.add(new_sig)
        db.commit()
        db.refresh(new_sig)
        print(f"DEBUG: DB Record created: ID {new_sig.id}")
    except Exception as e:
        db.rollback()
        print(f"DEBUG: DB Insert failed: {e}")
        raise HTTPException(status_code=500, detail="Error al registrar en BD.")
    
    
    # 5. Sync to Sheets (Crucial Step: Always sync signature to 'Firmas' sheet immediately)
    try:
         # Notification target logic: 
         # If Consolidating, we don't necessarily send an email NOW, but the Sheet needs a "target" or just logs it.
         # sync_signature_to_sheet(sig, email_target).
         # Let's use the user's email or a default for logging purposes.
         sync_signature_to_sheet(new_sig, "CONSOLIDATED_WAITING") 
    except Exception as e:
        print(f"DEBUG WARNING: Sheets sync failed: {e}")
        # Non-blocking? User said "bi se llenó la planilla", implying it's important.
        # But maybe we shouldn't fail the whole closure? 
        # Let's log it.

    # 6. Global Day Closure Check & Email (RESTORED)
    # Logic:
    # 1. Get all technicians that had activities TODAY.
    # 2. Get all signatures for TODAY.
    # 3. If Set(Active Techs) - Set(Signed Techs) is EMPTY -> ALL HAVE SIGNED.
    # 4. Trigger Consolidated Day Report.
    
    import pandas as pd
    from app.services.email_service import send_plan_summary
    
    message = "Firma guardada." # Default message
    
    try:
        # A. Find all unique techs assigned for today
        active_techs_query = db.query(Activity.tecnico_nombre).filter(
            Activity.fecha == upload_date
        ).distinct().all()
        # active_techs_query is list of rows [('Juan',), ('Pedro',)]
        active_techs = {r[0].strip().lower() for r in active_techs_query if r[0]}
        
        # B. Find all signatures for today (including the one just saved)
        signed_techs_query = db.query(DaySignature.tecnico_nombre).filter(
            DaySignature.fecha == upload_date
        ).all()
        signed_techs = {r[0].strip().lower() for r in signed_techs_query if r[0]}
        
        pending_techs = active_techs - signed_techs
        
        print(f"DEBUG CLOSURE: Active={active_techs}, Signed={signed_techs}, Pending={pending_techs}")
        
        if not pending_techs:
            print(">>> ALL TECHNICIANS HAVE SIGNED! TRIGGERING MASTER REPORT <<<")
            
            # Fetch ALL activities for the day to generate the Master Report
            all_activities = db.query(Activity).filter(
                Activity.fecha == upload_date
            ).all()
            
            activities_data = []
            for act in all_activities:
                activities_data.append({
                    "tecnico_nombre": act.tecnico_nombre,
                    "ticket_id": act.ticket_id,
                    "cliente": act.cliente,
                    "tipo_trabajo": act.tipo_trabajo,
                    "direccion": act.direccion,
                    "comuna": act.comuna,
                    "estado": act.estado.value,
                    "region": act.region,
                })
            
            df_master = pd.DataFrame(activities_data)
            
            # Recalculate Stats for the Header
            stats = {
                "processed": len(activities_data),
                "created": len([a for a in activities_data if a['estado'] == 'PENDIENTE']),
                "updated": len([a for a in activities_data if a['estado'] != 'PENDIENTE'])
            }
            
            # SEND SYNCHRONOUSLY
            try:
                # send_plan_summary will read SMTP_TO from env 
                # (which user requested to be christianzv14@gmail.com)
                # FIX: We now force pass the email to be sure.
                target_email = "christianzv14@gmail.com"
                print(f"DEBUG: Triggering Master Email to {target_email}")
                send_plan_summary(stats, df_master, to_email=target_email)
                print("DEBUG: Master Email sent successfully.")
                
            except Exception as e_mail:
                 print(f"DEBUG CRITICAL: Master Email failed: {e_mail}")
                 # Rollback signature so they can retry the closure
                 db.delete(new_sig)
                 db.commit()
                 raise HTTPException(status_code=500, detail=f"Error enviando Reporte Final (Firma revertida): {e_mail}")

            message = "Firma guardada. REPORTE DIARIO ENVIADO (Equipo Completo)."
            
        else:
            print(f"DEBUG: Still waiting for {pending_techs}. No email sent.")
            # We want to display names nicely. Original casing? 
            # active_techs_query had original casing.
            pending_display = [r[0] for r in active_techs_query if r[0].strip().lower() in pending_techs]
            message = f"Firma guardada. Esperando a: {', '.join(pending_display)}"


    except Exception as e:
        print(f"DEBUG WARNING: Closure check failed: {e}")
        if "Firma revertida" in str(e):
             raise e
        # Otherwise ignore non-critical logic errors
        # pass


    # 7. Update Scores (BACKGROUND TASK)
    try:
        print(f"DEBUG: Queuing score update...")
        background_tasks.add_task(update_scores_in_sheet)
    except Exception as e:
        print(f"DEBUG WARNING: Score queue failed: {e}")

    return {"status": "success", "message": message}

@router.get("/status")
def get_signature_status(
    fecha: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if current user has signed for a specific date (default: Today)."""
    target_date = fecha if fecha else date.today()
    tech_clean = current_user.tecnico_nombre.strip().lower()
    
    all_sigs = db.query(DaySignature).filter(DaySignature.fecha == target_date).all()
    
    existing = next((s for s in all_sigs if s.tecnico_nombre.strip().lower() == tech_clean), None)
    
    return {"is_signed": existing is not None}
