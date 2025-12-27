from sqlalchemy import text
from app.database import SessionLocal

def enforce_exact_tickets():
    print("--- ENFORCING EXACT TICKETS ---")
    db = SessionLocal()
    try:
        # Valid Tickets from User's Excel Screenshot + My Inspection (Step 1217)
        # Juan: 42944, 42965, 43007
        # Pedro: 42730, 42731
        valid_tickets = ['42944', '42965', '43007', '42730', '42731']
        
        # 1. Check what is currently there
        rows = db.execute(text("SELECT ticket_id, tecnico_nombre FROM activities")).fetchall()
        print(f"Current DB Count: {len(rows)}")
        
        # 2. Delete anything NOT in valid_tickets
        formatted_list = "', '".join(valid_tickets)
        query = f"DELETE FROM activities WHERE ticket_id NOT IN ('{formatted_list}')"
        
        db.execute(text(query))
        db.commit()
        
        print(f"-> Executed Purge. Only these remain: {valid_tickets}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    enforce_exact_tickets()
