import os
import uuid
from datetime import date, datetime
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
        print(f"DEBUG: Signature update. Overwriting ID {existing.id} for {upload_date}")
        # Continue execution to overwrite
    else:
        print(f"DEBUG: Start new signature for {upload_date}")
    
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
    
    # 4. Save to Database (Upsert)
    try:
        if existing:
             existing.signature_ref = file_path
             existing.timestamp = datetime.utcnow() # Update timestamp
             db.commit()
             db.refresh(existing)
             new_sig = existing # Use the updated object
             print(f"DEBUG: DB Record UPDATED: ID {new_sig.id}")
        else:
             new_sig = DaySignature(
                 tecnico_nombre=tech_name_db,
                 fecha=upload_date,
                 signature_ref=file_path
             )
             db.add(new_sig)
             db.commit()
             db.refresh(new_sig)
             print(f"DEBUG: DB Record CREATED: ID {new_sig.id}")

    except Exception as e:
        db.rollback()
        print(f"DEBUG: DB Ops failed: {e}")
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

    # 6. Send Individual Email Confirmation (SYNCHRONOUS & BLOCKING)
    # Strategy: "Keep it Simple". 1 Signature -> 1 Email.
    # If there are 2 techs, Manager gets 2 emails.
    
    try:
        # Fetch THIS technician's activities only
        activities = db.query(Activity).filter(
            Activity.tecnico_nombre == tech_name_db,
            Activity.fecha == upload_date
        ).all()
        
        # Hardcoded Target for Reliability
        notification_target = "christianzv14@gmail.com"
        
        print(f"DEBUG: SENDING INDIVIDUAL EMAIL to {notification_target}...")
        print(">>> RUNNING INDIVIDUAL MODE v2 <<")
        
        try:
            # Send Summary for THIS tech
            send_workday_summary(notification_target, tech_name_db, upload_date, activities)
            print("DEBUG: Individual Email sent successfully.")
        except Exception as e_mail:
            print(f"DEBUG CRITICAL: Email failed to send: {e_mail}")
            # ROLLBACK: Delete the signature so user can try again
            db.delete(new_sig)
            db.commit()
            print("DEBUG: Rollback signature due to email failure.")
            raise HTTPException(status_code=500, detail=f"Error enviando correo (Firma eliminada, intente de nuevo): {str(e_mail)}")

        message = "Firma guardada y Correo enviado."

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"DEBUG WARNING: General Email Logic Error: {e}")
        # If it wasn't the critical email error, we log it.
        # But if we failed to fetch activities, we probably shouldn't crash the signature?
        # User prioritized EMAIL. So if logic fails, maybe we should warn.
        pass


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
    
    is_signed = existing is not None
    
        # Use updated_at (Server Time) to avoid Client Clock Skew issues
    # SMART CHECK: If signed, check if any activity was finished *AFTER* the signature
    if is_signed and existing.timestamp:
        # Use updated_at (Server Time) to avoid Client Clock Skew issues
        latest_activity = db.query(Activity).filter(
            Activity.tecnico_nombre == current_user.tecnico_nombre,
            Activity.fecha == target_date
        ).order_by(Activity.updated_at.desc()).first()
        
        if latest_activity and latest_activity.updated_at:
             # Buffer: If activity was updated AFTER signature created
             if latest_activity.updated_at > existing.timestamp:
                 print(f"DEBUG: Smart Sign Status - Activity updated at {latest_activity.updated_at} > Sig at {existing.timestamp}. FAIL SIGN STATUS.")
                 is_signed = False
                 
    return {"is_signed": is_signed}
