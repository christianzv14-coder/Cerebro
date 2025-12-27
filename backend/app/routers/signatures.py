import os
import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import DaySignature, User
from app.deps import get_current_user
from app.services.sheets_service import sync_signature_to_sheet

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Main endpoint for Mobile App (Base64)."""
    return await _process_signature_upload(db, current_user, base64_str=upload_data.image_base64, fecha=upload_data.fecha)

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

async def _process_signature_upload(db, current_user, base64_str=None, file=None, fecha: Optional[date] = None):
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
    
    # 5. Sync to Sheets
    try:
        sync_signature_to_sheet(new_sig)
    except Exception as e:
        print(f"DEBUG WARNING: Sheets sync failed: {e}")
        return {"status": "success", "message": "Firma guardada localmente, error en Sheets."}
        
    return {"status": "success", "message": "Firma guardada y sincronizada correctamente."}

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
