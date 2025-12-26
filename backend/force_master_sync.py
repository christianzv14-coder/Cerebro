import sys
import os
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models.models import Activity
from app.services.sheets_service import sync_activity_to_sheet

def force_sync_all():
    db = SessionLocal()
    try:
        activities = db.query(Activity).all()
        print(f"Force syncing {len(activities)} activities...")
        for act in activities:
            try:
                sync_activity_to_sheet(act)
                print(f"  - {act.ticket_id}: Sync OK")
            except Exception as e:
                print(f"  - {act.ticket_id}: Sync FAILED: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    force_sync_all()
