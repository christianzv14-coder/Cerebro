from app.database import SessionLocal
from app.models.models import FailureReason

def populate_reasons():
    db = SessionLocal()
    reasons = [
        ('CLIENTE_AUSENTE', 'Cliente Ausente'),
        ('DIRECCION_INCORRECTA', 'Dirección Incorrecta'),
        ('FALLA_TECNICA', 'Falla Técnica'),
        ('RECHAZO_CLIENTE', 'Rechazo Cliente'),
        ('OTRO', 'Otro')
    ]
    
    try:
        for code, label in reasons:
            reason = db.query(FailureReason).filter(FailureReason.code == code).first()
            if not reason:
                reason = FailureReason(code=code, label=label)
                db.add(reason)
                print(f"Agregado: {code}")
            else:
                print(f"Ya existe: {code}")
        db.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    populate_reasons()
