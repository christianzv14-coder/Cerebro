from sqlalchemy import text
from app.database import SessionLocal

def delete_extras():
    print("--- DELETING EXTRA TASKS ---")
    db = SessionLocal()
    try:
        extras = ['41388', '42974']
        
        for t in extras:
            res = db.execute(text(f"DELETE FROM activities WHERE ticket_id = '{t}'"))
            print(f"Deleted Ticket {t}")
            
        db.commit()
        print("-> DONE. Extras removed.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    delete_extras()
