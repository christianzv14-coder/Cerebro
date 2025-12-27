from sqlalchemy import text
from app.database import SessionLocal

def debug_extra_tasks():
    print("--- DEBUG EXTRA TASKS ---")
    db = SessionLocal()
    try:
        extras = ['41388', '42974', '42730', '42731']
        
        for t in extras:
            row = db.execute(text(f"SELECT ticket_id, tecnico_nombre, fecha FROM activities WHERE ticket_id = '{t}'")).fetchone()
            if row:
                print(f"Ticket: {row[0]} | Assigned To: '{row[1]}' | Date: {row[2]}")
            else:
                print(f"Ticket: {t} NOT FOUND")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_extra_tasks()
