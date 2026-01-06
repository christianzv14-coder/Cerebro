from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import date
from app.database import get_db
from app.models.models import User, Role
from app.models.finance import Expense
from app.deps import get_current_user
from app.services.sheets_service import sync_expense_to_sheet, get_dashboard_data

router = APIRouter(tags=["finance"])

# --- Pydantic Schemas ---
class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    amount: int
    concept: str
    category: str
    section: Optional[str] = "OTROS"
    date: date
    payment_method: Optional[str] = None
    image_url: Optional[str] = None

# --- Endpoints ---

@router.post("/", response_model=ExpenseOut)
def create_expense(
    amount: int = Form(...),
    concept: str = Form(None),
    category: str = Form(...),
    payment_method: str = Form(...),
    section: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new expense linked to the authenticated user.
    """
    try:
        user = current_user

        image_url = None
        if image:
            import os
            import shutil
            from datetime import datetime
            
            upload_dir = "uploads/receipts"
            os.makedirs(upload_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{user.tecnico_nombre}_{timestamp}_{image.filename}"
            file_path = f"{upload_dir}/{filename}"
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            image_url = f"/uploads/receipts/{filename}"

        new_expense = Expense(
            user_id=user.id,
            amount=amount,
            concept=concept or "Gasto sin concepto",
            category=category,
            section=section,
            payment_method=payment_method,
            date=date.today(),
            image_url=image_url
        )
        db.add(new_expense)
        db.commit()
        db.refresh(new_expense)
        
        # Trigger Sync to Sheets
        try:
           sync_expense_to_sheet(new_expense, user.tecnico_nombre, section=section)
        except Exception as e:
            print(f"WARNING: Failed to sync expense to sheet: {e}")
        
        return new_expense
        
    except Exception as e:
        print(f"Error creating expense: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[ExpenseOut])
def get_my_expenses(
    db: Session = Depends(get_db)
):
    """
    Get all expenses. Public for testing.
    """
    return db.query(Expense).order_by(Expense.date.desc(), Expense.id.desc()).all()

@router.get("/dashboard")
def get_finance_dashboard(current_user: User = Depends(get_current_user)):
    """
    Get dashboard summary data for the authenticated user.
    """
    # Use the tecnico_nombre from the authenticated user
    data = get_dashboard_data(current_user.tecnico_nombre)
    if not data:
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data from sheets")
    return data

# --- Category Management ---
from app.services.sheets_service import add_category_to_sheet, delete_category_from_sheet

class CategoryCreate(BaseModel):
    section: str
    category: str
    budget: int = 0

class CategoryDelete(BaseModel):
    section: str
    category: str

@router.post("/categories/")
def create_category_endpoint(payload: CategoryCreate):
    """
    Add a new subcategory to a section in Sheets.
    """
    success = add_category_to_sheet(payload.section, payload.category, payload.budget)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add category to Sheets")
    return {"message": "Category added successfully"}

@router.delete("/categories/")
def delete_category_endpoint(payload: CategoryDelete, db: Session = Depends(get_db)):
    """
    Delete a subcategory from Sheets, but only if it has no expenses.
    """
    # Check if category has expenses in local DB
    has_expenses = db.query(Expense).filter(Expense.category == payload.category).first()
    if has_expenses:
        raise HTTPException(status_code=400, detail="No se puede borrar: tiene gastos asociados")

    success = delete_category_from_sheet(payload.section, payload.category)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found or failed to delete")
    return {"message": "Category deleted successfully"}

class CategoryUpdate(BaseModel):
    section: str
    category: str
    new_budget: int

@router.patch("/categories/")
def update_category_endpoint(payload: CategoryUpdate):
    """
    Update a subcategory's budget in Sheets.
    """
    # Assuming add_category_to_sheet also updates if it exists or we need a new service
    from app.services.sheets_service import update_category_in_sheet
    success = update_category_in_sheet(payload.section, payload.category, payload.new_budget)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update category")
    success = update_category_in_sheet(payload.section, payload.category, payload.new_budget)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update category")
    return {"message": "Category updated successfully"}

class UpdateBudgetSchema(BaseModel):
    new_budget: int

@router.post("/budget")
def update_global_budget_endpoint(payload: UpdateBudgetSchema, db: Session = Depends(get_db)):
    """
    Update the global monthly budget in Config sheet.
    """
    from app.services.sheets_service import update_monthly_budget
    success = update_monthly_budget(payload.new_budget)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update budget in Sheets")
    return {"message": "Budget updated successfully", "new_budget": payload.new_budget}
