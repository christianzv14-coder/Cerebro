from app.database import SessionLocal
from app.models.models import User, Role
from app.core.security import get_password_hash

def create_users():
    db = SessionLocal()
    try:
        # Define users to ensure exist
        users_to_create = [
            {
                "email": "juan.perez@cerebro.com",
                "tecnico_nombre": "Juan Perez",
                "password": "123456",
                "role": Role.TECH
            },
            {
                "email": "pedro@cerebro.com",
                "tecnico_nombre": "Pedro Pascal",
                "password": "123456",
                "role": Role.TECH
            }
        ]

        print("Verificando/Creando usuarios...")
        for u_data in users_to_create:
            user = db.query(User).filter(User.email == u_data["email"]).first()
            if not user:
                print(f" -> Creando usuario: {u_data['tecnico_nombre']}")
                new_user = User(
                    email=u_data["email"],
                    tecnico_nombre=u_data["tecnico_nombre"],
                    hashed_password=get_password_hash(u_data["password"]),
                    role=u_data["role"]
                )
                db.add(new_user)
            else:
                print(f" -> Usuario existe: {u_data['tecnico_nombre']}")
        
        db.commit()
        print("\n=== Procesamiento Finalizado ===")
        print("Credenciales disponibles:")
        for u in users_to_create:
            print(f" - Nombre: {u['tecnico_nombre']}")
            print(f"   Email : {u['email']}")
            print(f"   Clave : {u['password']}")

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_users()
