from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from app.database import get_db
from app.models.models import User
from app.models.finance import Commitment
from app.deps import get_current_user
from app.services.sheets_service import sync_commitment_to_sheet, delete_commitment_from_sheet

router = APIRouter(tags=["commitments"])

# --- Pydantic Schemas ---
class CommitmentBase(BaseModel):
    title: str
    type: str # 'DEBT', 'LOAN'
    total_amount: int
    due_date: Optional[date] = None
    status: Optional[str] = "PENDING"

class CommitmentCreate(CommitmentBase):
    pass

class CommitmentUpdate(BaseModel):
    paid_amount: Optional[int] = None
    status: Optional[str] = None
    title: Optional[str] = None
    due_date: Optional[date] = None

class CommitmentOut(CommitmentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    paid_amount: int
    created_at: datetime

# --- Endpoints ---

@router.get("/", response_model=List[CommitmentOut])
def get_commitments(
    db: Session = Depends(get_db)
):
    """
    Get all commitments for the default user (Carlos).
    """
    # For MVP, assuming user 'Carlos'
    # For MVP, assuming user 'Christian'
    user = db.query(User).filter(User.email == "christian.zv@cerebro.com").first()
    if not user:
        # Fallback to any user
        user = db.query(User).first()
        
    if not user:
        return []
    
    return db.query(Commitment).filter(Commitment.user_id == user.id).order_by(Commitment.status.desc(), Commitment.due_date.asc()).all()

@router.post("/", response_model=CommitmentOut)
def create_commitment(
    commitment: CommitmentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new commitment.
    """
    # Fallback/Find default user (Christian)
    user = db.query(User).filter(User.email == "christian.zv@cerebro.com").first()
    if not user:
        # Fallback to any user if Christian is not found (e.g. dev env)
        user = db.query(User).first()
        
    if not user:
        raise HTTPException(status_code=404, detail="Default user not found")

    new_commitment = Commitment(
        user_id=user.id,
        title=commitment.title,
        type=commitment.type,
        total_amount=commitment.total_amount,
        due_date=commitment.due_date,
        status=commitment.status or "PENDING"
    )
    
    db.add(new_commitment)
    db.commit()
    db.refresh(new_commitment)

    # Sync to Sheets
    # Need to run in background or direct? Direct for MVP.
    try:
        sync_commitment_to_sheet(new_commitment, user.tecnico_nombre)
    except Exception as e:
        print(f"WARNING: Sync commitment failed: {e}")

    return new_commitment

@router.patch("/{commitment_id}", response_model=CommitmentOut)
def update_commitment(
    commitment_id: int,
    update_data: CommitmentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update commitment (e.g., register payment).
    """
    comm = db.query(Commitment).filter(Commitment.id == commitment_id).first()
    if not comm:
        raise HTTPException(status_code=404, detail="Commitment not found")
        
    if update_data.paid_amount is not None:
        comm.paid_amount = update_data.paid_amount
    if update_data.status is not None:
        comm.status = update_data.status
    if update_data.title is not None:
        comm.title = update_data.title
    if update_data.due_date is not None:
        comm.due_date = update_data.due_date
        
    db.commit()
    db.refresh(comm)

    # Sync Update
    # Find user name?
    user_name = "Carlos" 
    user = db.query(User).filter(User.id == comm.user_id).first()
    if user: user_name = user.tecnico_nombre

    try:
        sync_commitment_to_sheet(comm, user_name)
    except Exception as e:
        print(f"WARNING: Sync commitment update failed: {e}")

    return comm

@router.delete("/{commitment_id}")
def delete_commitment(
    commitment_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete commitment.
    """
    comm = db.query(Commitment).filter(Commitment.id == commitment_id).first()
    if not comm:
        raise HTTPException(status_code=404, detail="Commitment not found")
        
    db.delete(comm)
    db.commit()

    # Sync Delete
    try:
        delete_commitment_from_sheet(commitment_id)
    except Exception as e:
        print(f"WARNING: Sync commitment delete failed: {e}")

    return {"message": "Commitment deleted"}
