from fastapi import APIRouter, Depends
from app.schemas import UserResponse
from app.deps import get_current_user
from app.models.models import User, ActivityState
from datetime import datetime

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

@router.get("/debug/email")
def trigger_debug_email(current_user: User = Depends(get_current_user)):
    """
    Forces a test email to be sent to the current user (or test overrides).
    """
    from app.services.email_service import send_workday_summary
    from app.models.models import Activity
    from datetime import date
    import os
    
    # Create dummy activities
    dummy_acts = [
        Activity(
            tecnico_nombre="Test Tech",
            cliente="Test Client",
            tipo_trabajo="Test Work",
            estado=ActivityState.EXITOSO,
            resultado_motivo="Test Reason",
            fecha=date.today(),
            hora_inicio=datetime.utcnow(),
            hora_fin=datetime.utcnow()
        )
    ]
    
    recipient = "christianzv14@gmail.com" # Force for testing
    
    try:
        send_workday_summary(recipient, "Test Technician", date.today(), dummy_acts)
        return {"status": "success", "message": f"Test email sent to {recipient}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
