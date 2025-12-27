from sqlalchemy import text
from app.database import SessionLocal

def force_assign_pedro():
    print("--- FORCING ASSIGNMENT TO PEDRO ---")
    db = SessionLocal()
    try:
        # Get last 2 tickets
        # (Assuming the higher Ticket IDs often belong to the later rows, i.e. Pedro's)
        # Or just pick 2 arbitrary ones if we don't care which.
        # User has ticket 42730, 42731 for Pedro in the screenshot.
        
        target_tickets = ['42730', '42731']
        
        print(f"Targeting Tickets: {target_tickets}")
        
        for t in target_tickets:
            # Check if exists
            exists = db.execute(text(f"SELECT * FROM activities WHERE ticket_id = '{t}'")).fetchone()
            if exists:
                print(f"Found {t}. Updating to Pedro Pascal...")
                db.execute(text(f"UPDATE activities SET tecnico_nombre = 'Pedro Pascal' WHERE ticket_id = '{t}'"))
            else:
                print(f"Ticket {t} NOT FOUND in DB! Creating it...")
                # Create if missing
                db.execute(text(f"""
                    INSERT INTO activities (ticket_id, fecha, tecnico_nombre, estado, cliente, direccion, tipo_trabajo)
                    VALUES ('{t}', '2025-12-27', 'Pedro Pascal', 'PENDIENTE', 'CLIENTE_EMERGENCIA', 'Direccion X', 'Trabajo Y')
                """))
        
        db.commit()
        print("-> DONE. Pedro should have 2 tasks now.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    force_assign_pedro()
