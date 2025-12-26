from app.database import SessionLocal
from app.models.models import Activity, ActivityState
from datetime import date

def force_close():
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
             a.estado = ActivityState.EXITOSO
             print(f" - Fixed: {a.ticket_id} -> EXITOSO")
        
        db.commit()
        print("Done. All Juan Perez activities are now closed.")
    finally:
        db.close()

if __name__ == "__main__":
    force_close()
