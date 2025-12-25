from app.database import SessionLocal, engine, Base
from app.models.models import User, Role
from app.core.security import get_password_hash
from app.services.excel_service import process_excel_upload
import pandas as pd
import io
from datetime import date, timedelta

def init_data():
    db = SessionLocal()
    try:
        print("1. Creando usuario Admin...")
        admin_email = "admin@cerebro.com"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                tecnico_nombre="Admin General",
                hashed_password=get_password_hash("123456"),
                role=Role.ADMIN
            )
            db.add(admin)
            db.commit()
            print(f" -> Admin creado: {admin_email} / 123456")
        else:
            print(" -> Admin ya existe.")

        print("\n2. Generando y Cargando Datos de Prueba...")
        # Generar datos dummy
        data = {
            'fecha': [date.today(), date.today(), date.today() + timedelta(days=1)],
            'ticket_id': ['TKT-001', 'TKT-002', 'TKT-003'],
            'tecnico_nombre': ['Juan Perez', 'Juan Perez', 'Maria Gonzalez'],
            'patente': ['AB-1234', 'CD-5678', 'EF-9012'],
            'cliente': ['Transportes Fast', 'Logistica Global', 'Chile Trucks'],
            'direccion': ['Av. Kennedy 111', 'Ruta 68 km 10', 'Panamericana Norte 5000'],
            'tipo_trabajo': ['Instalacion GPS', 'Revision Sensor', 'Desinstalacion']
        }
        df = pd.read_json(pd.DataFrame(data).to_json()) # Trick to sanitize dates if needed, but DataFrame is fine
        df = pd.DataFrame(data)
        
        # Guardar en disco para referencia
        df.to_excel('mock_data.xlsx', index=False)
        print(" -> Archivo 'mock_data.xlsx' generado en disco.")
        
        # Cargar en DB usando el servicio
        # Convert df to excel bytes in memory to simulate upload
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        
        stats = process_excel_upload(output, db)
        print(f" -> Datos cargados exitosamente: {stats}")
        
        print("\n=== INICIALIZACIÓN COMPLETA ===")
        print("Usuarios creados automáticamente:")
        print(" - Juan Perez (Login: juan.perez@cerebro.com / 123456)")
        print(" - Maria Gonzalez (Login: maria.gonzalez@cerebro.com / 123456)")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_data()
