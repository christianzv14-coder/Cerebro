
from sqlalchemy import create_engine, text
from app.core.config import settings
from datetime import date

engine = create_engine(settings.DATABASE_URL)
today = date.today()

print(f"--- CHECKING FOR DATE: {today} ---")

with engine.connect() as conn:
    # 1. Active Techs
    sql_active = text("SELECT DISTINCT tecnico_nombre FROM activities WHERE fecha = :today")
    result_active = conn.execute(sql_active, {"today": today})
    active_techs = [row[0] for row in result_active]
    print(f"ACTIVE TECHNICIANS (Activity Table): {active_techs}")

    # 2. Signed Techs
    sql_signed = text("SELECT DISTINCT tecnico_nombre FROM day_signatures WHERE fecha = :today")
    result_signed = conn.execute(sql_signed, {"today": today})
    signed_techs = [row[0] for row in result_signed]
    print(f"SIGNED TECHNICIANS (Signatures Table): {signed_techs}")

    pending = set(t.strip().lower() for t in active_techs if t) - set(t.strip().lower() for t in signed_techs if t)
    print(f"PENDING CLOSURE: {pending}")
