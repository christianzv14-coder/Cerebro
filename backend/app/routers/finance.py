from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile, BackgroundTasks
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
    background_tasks: BackgroundTasks,
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
        
        # Prepare data for background sync (avoid passing SQLAlchemy objects)
        expense_data = {
            "date": str(new_expense.date),
            "concept": new_expense.concept,
            "category": new_expense.category,
            "amount": new_expense.amount,
            "payment_method": new_expense.payment_method,
            "image_url": new_expense.image_url
        }
        
        # Trigger Sync to Sheets in Background
        background_tasks.add_task(sync_expense_to_sheet, expense_data, user.tecnico_nombre, section=section)
        
        return new_expense
        
    except Exception as e:
        print(f"Error creating expense: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an expense.
    """
    from app.services.sheets_service import delete_expense_from_sheet
    
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.user_id == current_user.id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found or not owned by you")

    # Prepare data for sheets deletion
    expense_data = {
        "date": str(expense.date),
        "concept": expense.concept,
        "amount": expense.amount
    }
    
    try:
        # We do this before deleting from DB so we have the data
        delete_expense_from_sheet(expense_data, current_user.tecnico_nombre)
        
        db.delete(expense)
        db.commit()
        return {"message": "Expense deleted successfully"}
    except Exception as e:
        db.rollback()
        print(f"Error deleting expense: {e}")
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
    new_category: Optional[str] = None

@router.patch("/categories/")
def update_category_endpoint(payload: CategoryUpdate, db: Session = Depends(get_db)):
    """
    Update a subcategory's budget in Sheets, and optionally rename it (updating history).
    """
    from app.services.sheets_service import update_category_in_sheet
    
    old_cat = payload.category
    new_cat = payload.new_category or old_cat
    
    # If name changed, update local DB history first
    if new_cat != old_cat:
        print(f"DEBUG [BACKEND] Renaming category from '{old_cat}' to '{new_cat}' in local DB...")
        updated_count = db.query(Expense).filter(Expense.category == old_cat, Expense.section == payload.section).update({Expense.category: new_cat})
        db.commit()
        print(f"DEBUG [BACKEND] Internal history updated: {updated_count} rows.")

    success = update_category_in_sheet(payload.section, old_cat, payload.new_budget, new_cat=payload.new_category)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update category in Sheets")
    
    return {"message": "Category updated successfully", "new_category": new_cat}

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
