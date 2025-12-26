from app.database import SessionLocal
from app.models.models import Activity, User
import sys

def verify_new_fields():
    print("--- VERIFYING NEW FIELDS ---")
    db = SessionLocal()
    try:
        # Check one activity that should have data
        # Assuming the generated plantilla has data.
        # If it was generated from Coordinados (11).xlsx, it should have 116 rows.
        
        users_count = db.query(User).count()
        print(f"Users in DB: {users_count}")
        
        activities = db.query(Activity).all()
        if not activities:
            print("ERROR: No activities found in DB.")
            return
            
        print(f"Found {len(activities)} activities. Checking first 3:")
        for act in activities[:3]:
            print(f"\n--- Ticket: {act.ticket_id} ---")
            print(f" - Tipo Trabajo: {act.tipo_trabajo}")
            print(f" - Direccion: {act.direccion}")
            print(f" - Prioridad: {act.prioridad}")
            print(f" - Accesorios: {act.accesorios}")
            print(f" - Comuna: {act.comuna}")
            print(f" - Region: {act.region}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_new_fields()
