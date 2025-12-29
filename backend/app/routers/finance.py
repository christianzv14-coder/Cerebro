from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import date
from app.database import get_db
from app.models.models import User
from app.models.finance import Expense
from app.deps import get_current_user
from app.services.sheets_service import sync_expense_to_sheet

router = APIRouter(prefix="/expenses", tags=["finance"])

# --- Pydantic Schemas ---
class ExpenseCreate(BaseModel):
    amount: int
    concept: str
    category: str
    date: date
    image_url: str = None

class ExpenseOut(BaseModel):
    id: int
    amount: int
    concept: str
    category: str
    date: date
    image_url: str = None
    
    class Config:
        orm_mode = True

# --- Endpoints ---

@router.post("/", response_model=ExpenseOut)
def create_expense(
    amount: int = Form(...),
    concept: str = Form(...),
    category: str = Form(...),
    image: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new expense with optional receipt image.
    """
    try:
        image_url = None
        if image:
            # Save the image
            import os
            import shutil
            from datetime import datetime
            
            # Create directory if not exists
            upload_dir = "uploads/receipts"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{current_user.tecnico_nombre}_{timestamp}_{image.filename}"
            file_path = f"{upload_dir}/{filename}"
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            # Construct URL (assuming static mount at /uploads)
            # We need to access settings.BASE_URL or build it dynamically
            # For now, store relative path or assume a domain
            image_url = f"/uploads/receipts/{filename}"

        new_expense = Expense(
            user_id=current_user.id,
            amount=amount,
            concept=concept,
            category=category,
            date=date.today(),
            image_url=image_url
        )
        db.add(new_expense)
        db.commit()
        db.refresh(new_expense)
        
        # Trigger Sync to Sheets
        try:
           sync_expense_to_sheet(new_expense, current_user.tecnico_nombre)
        except Exception as e:
            print(f"WARNING: Failed to sync expense to sheet: {e}")
        
        return new_expense
        
    except Exception as e:
        print(f"Error creating expense: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[ExpenseOut])
def get_my_expenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all expenses for the current user, ordered by date desc.
    """
    return db.query(Expense).filter(Expense.user_id == current_user.id).order_by(Expense.date.desc(), Expense.id.desc()).all()
