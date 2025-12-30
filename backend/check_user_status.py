
from sqlalchemy import create_engine, text
from app.core.config import settings

# Force autocommit
engine = create_engine(settings.DATABASE_URL, execution_options={"isolation_level": "AUTOCOMMIT"})

with engine.connect() as conn:
    print("--- CHECKING USER 'Juan Perez' ---")
    try:
        res = conn.execute(text("SELECT id, username, email, tecnico_nombre, role, is_active FROM users WHERE tecnico_nombre = 'Juan Perez'")).fetchone()
        
        if res:
            print(f"FOUND: ID={res[0]}, User={res[1]}, Email={res[2]}, Name={res[3]}, Active={res[5]}")
        else:
            print("❌ CRITICAL: User 'Juan Perez' NOT FOUND.")
            
        # Also check generic search to see who is left
        print("\n--- ALL USERS ---")
        all_users = conn.execute(text("SELECT id, tecnico_nombre, username, email FROM users")).fetchall()
        for u in all_users:
            print(u)
    except Exception as e:
        print(f"Error: {e}")
