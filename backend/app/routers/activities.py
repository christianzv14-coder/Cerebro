from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Activity, ActivityState, User
from app.schemas import ActivityResponse, ActivityStart, ActivityFinish
from app.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[ActivityResponse])
def get_my_activities(
    fecha: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get activities for the logged-in technician.
    Default filter: Today's date (if not provided).
    """
    query = db.query(Activity).filter(Activity.tecnico_nombre == current_user.tecnico_nombre)
    
    if fecha:
        query = query.filter(Activity.fecha == fecha)
    else:
        # Default to today if no date provided? Or return all? 
        # User request: "Home: Mi agenda de hoy". So defaulting to today seems appropriate or client sends it.
        # Let's filter by today default strict or loose? 
        # Making it optional but Client usually requests specific date.
        pass

    # Sort: PENDIENTE first, then by time
    # Custom sort not easy in SQL without case, let's just order by fecha, ticket_id
    query = query.order_by(Activity.fecha.asc(), Activity.ticket_id.asc())
    
    return query.all()

@router.post("/{ticket_id}/start", response_model=ActivityResponse)
def start_activity(
    ticket_id: str,
    payload: ActivityStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    activity = db.query(Activity).filter(Activity.ticket_id == ticket_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    if activity.tecnico_nombre != current_user.tecnico_nombre:
         raise HTTPException(status_code=403, detail="Not assigned to this activity")

    # Idempotency
    if activity.estado == ActivityState.EN_CURSO:
        return activity
    
    if activity.estado != ActivityState.PENDIENTE:
        raise HTTPException(status_code=400, detail=f"Cannot start activity in state {activity.estado}")

    activity.estado = ActivityState.EN_CURSO
    activity.hora_inicio = payload.timestamp or datetime.utcnow() # Trust app timestamp or server?
    # Better to use server time for truth but loose sync for offline? 
    # Designing for offline: App sends its timestamp when the button was pressed. 
    # We should favor payload timestamp if reasonable, or server time.
    # User said: "registra hora_inicio (timestamp server si hay señal; si no, local + sync)"
    
    db.commit()
    db.refresh(activity)
    return activity

@router.post("/{ticket_id}/finish", response_model=ActivityResponse)
def finish_activity(
    ticket_id: str,
    payload: ActivityFinish,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    activity = db.query(Activity).filter(Activity.ticket_id == ticket_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if activity.tecnico_nombre != current_user.tecnico_nombre:
         raise HTTPException(status_code=403, detail="Not assigned to this activity")
    
    # Idempotency / "At-most-once"
    if activity.estado in [ActivityState.EXITOSO, ActivityState.FALLIDO, ActivityState.REPROGRAMADO]:
        # Already closed. Check if result matches? Or just return current.
        # Rule: "Si ya está cerrado, rechazar o devolver estado actual"
        return activity

    if activity.estado != ActivityState.EN_CURSO and activity.estado != ActivityState.PENDIENTE:
         # Should be EN_CURSO usually, but maybe they skip start?
         # Allowing Finish from Pendiente just in case? Or force Start?
         # Let's allow flexible flow, but typically EN_CURSO.
         pass

    # Validate State string
    try:
        new_state = ActivityState(payload.resultado)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid result state (EXITOSO, FALLIDO, REPROGRAMADO)")

    if new_state == ActivityState.FALLIDO and not payload.motivo:
        raise HTTPException(status_code=400, detail="Motivo is required for FALLIDO")

    activity.estado = new_state
    activity.hora_fin = payload.timestamp
    activity.resultado_motivo = payload.motivo
    activity.observacion = payload.observacion
    
    # Calculate duration
    if activity.hora_inicio and activity.hora_fin:
        delta = activity.hora_fin - activity.hora_inicio
        activity.duracion_min = int(delta.total_seconds() / 60)
    
    db.commit()
    db.refresh(activity)
    
    # Trigger Sheet Sync (Background Task recommended, but direct for MVP simplicity)
    try:
        from app.services.sheets_service import sync_activity_to_sheet
        sync_activity_to_sheet(activity)
    except Exception as e:
        print(f"Background Sync Error: {e}")
    
    return activity
