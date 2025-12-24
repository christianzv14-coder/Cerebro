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
