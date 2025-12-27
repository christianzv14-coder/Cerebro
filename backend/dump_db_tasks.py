from sqlalchemy import text
from app.database import SessionLocal

def dump_db_tasks():
    print("--- FULL DB TASK DUMP ---")
    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT ticket_id, tecnico_nombre, cliente, direccion, tipo_trabajo FROM activities")).fetchall()
        print(f"Total Rows: {len(rows)}")
        for r in rows:
            print(f"Ticket: {r[0]} | Tech: {r[1]}")
            print(f"    Client: {r[2]}")
            print(f"    Addr:   {r[3]}")
            print(f"    Type:   {r[4]}")
            print("-" * 20)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    dump_db_tasks()
