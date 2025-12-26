from app.database import SessionLocal
from app.models.models import User, Activity
from datetime import date

def inspect_data():
    db = SessionLocal()
    try:
        print("=== USUARIOS ===")
        users = db.query(User).all()
        for u in users:
            print(f"ID: {u.id}, Nombre: '{u.tecnico_nombre}', Email: {u.email}")

        print("\n=== ACTIVIDADES DE HOY ===")
        today = date.today()
        activities = db.query(Activity).filter(Activity.fecha == today).all()
        if not activities:
            print("No hay actividades para hoy.")
        else:
            for a in activities:
                print(f"Ticket: {a.ticket_id}, Técnico: '{a.tecnico_nombre}', Estado: {a.estado}")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_data()
