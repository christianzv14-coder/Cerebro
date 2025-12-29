
from sqlalchemy import text
from app.database import SessionLocal

db = SessionLocal()

try:
    print("--- USERS ---")
    result = db.execute(text("SELECT id, tecnico_nombre, email FROM users"))
    for row in result:
        print(row)

    print("\n--- ACTIVITIES (Recent) ---")
    # Check for today and the 19th just in case
    result = db.execute(text("SELECT id, fecha, tecnico_nombre, ticket_id FROM activities WHERE fecha >= '2025-12-01' ORDER BY fecha DESC"))
    for row in result:
        print(row)

except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
