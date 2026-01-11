from fastapi import FastAPI
import os
from app.core.config import settings
from app.database import engine, Base
from fastapi.staticfiles import StaticFiles
from app.routers import auth, users, activities, admin, signatures, finance, commitments
from app.models.finance import Expense  # Import to register with Base

# Create tables on startup (simple for MVP)
Base.metadata.create_all(bind=engine)

def init_user():
    from app.database import SessionLocal
    from app.models.models import User, Role
    from app.core.security import get_password_hash
    db = SessionLocal()
    try:
        chr_email = "christian.zv@cerebro.com"
        christian = db.query(User).filter(User.email == chr_email).first()
        hashed_pwd = get_password_hash("123456")
        
        if not christian:
            print(f"Creating user {chr_email}...")
            christian = User(
                email=chr_email,
                tecnico_nombre="Christian ZV",
                hashed_password=hashed_pwd,
                role=Role.ADMIN,
                is_active=True
            )
            db.add(christian)
        else:
            print(f"Updating password for {chr_email}...")
            christian.hashed_password = hashed_pwd
            christian.is_active = True
        
        db.commit()
    except Exception as e:
        print(f"Error initializing user: {e}")
    finally:
        db.close()

init_user()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... (omitted) ...

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(activities.router, prefix=f"{settings.API_V1_STR}/activities", tags=["activities"])
app.include_router(signatures.router, prefix=f"{settings.API_V1_STR}/signatures", tags=["signatures"])
app.include_router(finance.router, prefix=f"{settings.API_V1_STR}/expenses", tags=["finance"])
app.include_router(commitments.router, prefix=f"{settings.API_V1_STR}/commitments", tags=["commitments"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])

from fastapi.responses import FileResponse

# Serve Static Files (Frontend) using absolute path to be safe in Docker
# "app/static" relative to where uvicorn is run (usually /app)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/debug-deploy")
def debug_deploy():
    import os
    return {
        "version": "v4.0.0-GoogleCloud",
        "cwd": os.getcwd(),
        "files_in_static": os.listdir("app/static") if os.path.exists("app/static") else "not found",
        "env_check": "GCP" if "K_SERVICE" in os.environ else ("RAILWAY" if "RAILWAY_STATIC_URL" in os.environ else "LOCAL"),
        "database": "PostgreSQL" if os.getenv("DATABASE_URL", "").startswith("postgresql") else "SQLite"
    }

@app.get("/")
def read_root():
    return FileResponse("app/static/index.html")

@app.get("/manifest.json")
def get_manifest():
    return FileResponse("app/static/manifest.json")

@app.get("/sw.js")
def get_sw():
    return FileResponse("app/static/sw.js")

@app.get("/icon-512.png")
def get_icon():
    return FileResponse("app/static/icon-512.png")



print("--- STARTING CEREBRO v4.0 GOOGLE CLOUD ---")
