from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import os

db_url = settings.FINANCE_DATABASE_URL

# Ensure SQLite uses absolute path in Docker environment
if db_url.startswith("sqlite"):
    if "./" in db_url:
        # Get the directory of database.py and go up to backend/
        base_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(base_dir)
        # Construct absolute path for the db file
        db_file = db_url.replace("sqlite:///./", "")
        db_url = f"sqlite:///{os.path.join(backend_dir, db_file)}"
    
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
