from sqlalchemy import text
from app.database import SessionLocal

def clear_activities():
    print("--- CLEARING ALL ACTIVITIES ---")
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE activities CASCADE"))
        # Also clear signatures to be safe?
        db.execute(text("TRUNCATE TABLE day_signatures CASCADE"))
        db.commit()
        print(" -> All activities deleted.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_activities()
