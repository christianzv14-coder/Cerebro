from app.database import SessionLocal
from app.models.models import Activity, ActivityState
from datetime import date

def reset_to_pending():
    db = SessionLocal()
    try:
        today = date.today()
        # Find activities for Juan Perez today
        activities = db.query(Activity).filter(
            Activity.tecnico_nombre == "Juan Perez",
            Activity.fecha == today
        ).all()
        
        print(f"Found {len(activities)} activities for Juan Perez today.")
        for a in activities:
             a.estado = ActivityState.PENDIENTE
             a.hora_inicio = None
             a.hora_fin = None
             print(f" - Reset: {a.ticket_id} -> PENDIENTE")
        
        db.commit()
        print("Done. All Juan Perez activities are now PENDIENTE.")
    finally:
        db.close()

if __name__ == "__main__":
    reset_to_pending()
