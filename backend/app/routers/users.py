from fastapi import APIRouter, Depends
from app.schemas import UserResponse
from app.deps import get_current_user
from app.models.models import User

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
