from app.database import SessionLocal
from app.models.models import Activity, DaySignature
from datetime import date

def clean():
    db = SessionLocal()
    today = date.today()
    print(f"Cleaning for date: {today}")
    
    # Clean Activities
    deleted_acts = db.query(Activity).filter(Activity.fecha == today).delete()
    print(f"Deleted {deleted_acts} activities.")
    
    # Clean Signatures
    deleted_sigs = db.query(DaySignature).filter(DaySignature.fecha == today).delete()
    print(f"Deleted {deleted_sigs} signatures.")
    
    db.commit()
    db.close()

if __name__ == "__main__":
    clean()
