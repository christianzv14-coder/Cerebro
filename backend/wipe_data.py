from app.database import SessionLocal
from app.models.models import Activity, DaySignature
from sqlalchemy import text

def wipe_all_data():
    db = SessionLocal()
    try:
        print("--- INICIANDO BORRADO TOTAL DE DATOS ---")
        
        # Delete Signatures first
        deleted_sigs = db.query(DaySignature).delete()
        print(f"Firmas eliminadas: {deleted_sigs}")
        
        # Delete Activities
        deleted_acts = db.query(Activity).delete()
        print(f"Actividades eliminadas: {deleted_acts}")
        
        db.commit()
        print("--- SISTEMA LIMPIO: LISTO PARA PRUEBA END-TO-END ---")
        
    except Exception as e:
        print(f"ERROR borrando datos: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    wipe_all_data()
