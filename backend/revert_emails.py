
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, execution_options={"isolation_level": "AUTOCOMMIT"})

# Mapping valid names to OFFICIAL emails
RESTORATION_MAP = {
    "Juan Perez": "juan.perez@cerebro.com",
    "Pedro Pascal": "pedro.pascal@cerebro.com"
}

with engine.connect() as conn:
    print("--- REVERTING EMAILS TO OFFICIAL ---")
    
    for name, official_email in RESTORATION_MAP.items():
        print(f"Restoring {name} -> {official_email}...")
        try:
            conn.execute(text(f"UPDATE users SET email = '{official_email}' WHERE tecnico_nombre = '{name}'"))
            print("✅ Restored.")
        except Exception as e:
            print(f"❌ Error: {e}")
            
    print("DONE.")
