from app.database import SessionLocal
from app.models.models import Activity
from app.services.sheets_service import sync_activity_to_sheet
import sys

def force_sync():
    db = SessionLocal()
    try:
        # Find an activity for Pedro Pascal to test (or any activity)
        # using a known ID or just the first one
        activity = db.query(Activity).filter(Activity.tecnico_nombre == "Pedro Pascal").first()
        
        if not activity:
            # Fallback to Juan Perez 
             activity = db.query(Activity).first()
        
        if not activity:
            print("No activities found in DB to sync.")
            return

        print(f"--- Force Syncing Activity: {activity.ticket_id} ({activity.tecnico_nombre}) ---")
        print(f"Priority: {activity.prioridad}, Accesor: {activity.accesorios}, Comuna: {activity.comuna}")
        
        sync_activity_to_sheet(activity)
        
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    force_sync()
