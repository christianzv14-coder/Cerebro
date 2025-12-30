from fastapi import APIRouter, Depends
from app.schemas import UserResponse
from app.deps import get_current_user
from app.models.models import User

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/me/scores")
def get_my_scores(current_user: User = Depends(get_current_user)):
    from app.services.sheets_service import get_technician_scores
    
    if not current_user.tecnico_nombre:
        return {"error": "User has no technical name assigned"}
        
    data = get_technician_scores(current_user.tecnico_nombre)
    if not data:
        return {
            "technician": current_user.tecnico_nombre,
            "total_points": 0,
            "total_money": 0,
            "history": []
        }
    return data
