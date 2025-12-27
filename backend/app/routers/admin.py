from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.deps import get_current_admin
from app.services.excel_service import process_excel_upload

router = APIRouter()

@router.post("/upload_excel")
def upload_planification(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin), # Only Admin
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
         raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    
    try:
        # Read file into memory? 
        # SpooledTemporaryFile is file-like.
        contents = file.file.read()
        
        # Reset cursor? Pandas read_excel accepts bytes or file-like. 
        # But read() might have consumed it. 
        # Let's pass the file.file directly if possible, or BytesIO.
        from io import BytesIO
        io_file = BytesIO(contents)
        
        stats = process_excel_upload(io_file, db)
        return {"message": "Upload successful", "stats": stats}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/test_email")
def test_email_configuration(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to test email sending using server env vars.
    """
    import pandas as pd
    from app.services.email_service import send_plan_summary
    
    # Mock Data
    stats = {"processed": 10, "created": 5, "updated": 5}
    df = pd.DataFrame({
        "tecnico_nombre": ["Tech A", "Tech B", "Tech A"],
        "comuna": ["Comuna 1", "Comuna 2", "Comuna 1"]
    })
    
    try:
        send_plan_summary(stats, df)
        return {"message": "Email sent successfully (Check inbox/spam)."}
    except Exception as e:
        return {"error": str(e), "detail": "Check SMTP variables in Railway."}
