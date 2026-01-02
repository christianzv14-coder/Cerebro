from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import os

db_url = settings.DATABASE_URL
print(f"DEBUG [DB]: Using DATABASE_URL = {db_url}")

# Ensure SQLite uses absolute path in Docker
if db_url.startswith("sqlite"):
    if "./" in db_url:
        # Convert relative to absolute based on current file location
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_url = db_url.replace("./", os.path.join(os.path.dirname(base_dir), ""))
    
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
