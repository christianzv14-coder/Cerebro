from app.database import SessionLocal
from app.models.models import Activity, ActivityState, User
from datetime import date

def create_real_data():
    db = SessionLocal()
    try:
        today = date.today()
        tech_name = "Juan Perez"
        
        # Ensure user exists
        user = db.query(User).filter(User.tecnico_nombre == tech_name).first()
        if not user:
            print(f"Error: User {tech_name} not found.")
            return

        # Clear existing activities for today to start fresh
        db.query(Activity).filter(Activity.fecha == today, Activity.tecnico_nombre == tech_name).delete()
        
        activities = [
            Activity(
                ticket_id="TKT-001",
                fecha=today,
                tecnico_nombre=tech_name,
                patente="AB-1234",
                cliente="Transportes Fas",
                direccion="Av. Kennedy 111",
                tipo_trabajo="Instalacion GPS",
                estado=ActivityState.PENDIENTE
            ),
            Activity(
                ticket_id="TKT-002",
                fecha=today,
                tecnico_nombre=tech_name,
                patente="CD-5678",
                cliente="Logistica Global",
                direccion="Ruta 68 km 10",
                tipo_trabajo="Revision Sensor",
                estado=ActivityState.PENDIENTE
            )
        ]
        
        db.add_all(activities)
        db.commit()
        print(f"Éxito! Creadas actividades TKT-001 y TKT-002 para hoy ({today}) con datos reales.")
        
    except Exception as e:
        db.rollback()
        print(f"Error creando data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_real_data()
