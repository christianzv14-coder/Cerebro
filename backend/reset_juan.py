from app.database import SessionLocal
from app.models.models import Activity, ActivityState
from datetime import date

def reset_all_juan():
    db = SessionLocal()
    try:
        today = date.today()
        # Find activities for ANY Juan Perez version
        all_activities = db.query(Activity).filter(Activity.fecha == today).all()
        
        targets = [a for a in all_activities if "juan" in a.tecnico_nombre.lower()]
        
        print(f"Found {len(targets)} activities matching 'juan' today.")
        for a in targets:
             a.estado = ActivityState.PENDIENTE
             a.hora_inicio = None
             a.hora_fin = None
             print(f" - Reset: {a.ticket_id} (Tech: {a.tecnico_nombre}) -> PENDIENTE")
        
        db.commit()
        print("Done. All Juan variations are now PENDIENTE.")
    finally:
        db.close()

if __name__ == "__main__":
    reset_all_juan()
