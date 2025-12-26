from app.database import SessionLocal
from app.models.models import Activity

def clear_all():
    db = SessionLocal()
    try:
        num = db.query(Activity).delete()
        db.commit()
        print(f"Deleted {num} activities. The App should now be empty.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_all()
