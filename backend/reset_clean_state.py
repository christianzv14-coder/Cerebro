from app.database import SessionLocal
from app.models.models import Activity, ActivityState, DaySignature

def reset_all():
    db = SessionLocal()
    try:
        print("--- INICIANDO RESET COMPLETO ---")
        
        # 1. Eliminar todas las firmas
        num_firmas = db.query(DaySignature).delete()
        print(f"1. Firmas eliminadas: {num_firmas}")
        
        # 2. Resetear todas las actividades a PENDIENTE
        # Reset fields: estado, horas, resultado, observacion
        num_activities = db.query(Activity).update({
            Activity.estado: ActivityState.PENDIENTE,
            Activity.hora_inicio: None,
            Activity.hora_fin: None,
            Activity.duracion_min: None,
            Activity.resultado_motivo: None,
            Activity.observacion: None
        }, synchronize_session=False)
        
        db.commit()
        print(f"2. Actividades reseteadas a PENDIENTE: {num_activities}")
        print("--- PROCESO FINALIZADO CON ÉXITO ---")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_all()
