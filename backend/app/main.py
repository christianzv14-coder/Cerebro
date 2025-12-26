from fastapi import FastAPI
import os
from app.core.config import settings
from app.database import engine, Base
from fastapi.staticfiles import StaticFiles
from app.routers import auth, users, activities, admin, signatures

# Create tables on startup (simple for MVP)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Request Logger Middleware
@app.middleware("http")
async def log_requests(request, call_next):
    method = request.method
    path = request.url.path
    print(f"\n[!!!] INCOMING: {method} {path}")
    try:
        response = await call_next(request)
        print(f"[!!!] OUTGOING: {method} {path} -> STATUS {response.status_code}")
        return response
    except Exception as e:
        print(f"[!!!] CRITICAL ERROR on {method} {path}: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": str(e)})

# Static Files for signatures
os.makedirs("uploads/signatures", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(activities.router, prefix=f"{settings.API_V1_STR}/activities", tags=["activities"])
app.include_router(signatures.router, prefix=f"{settings.API_V1_STR}/signatures", tags=["signatures"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])

@app.get("/")
def root():
    return {"status": "online", "version": "3.0-SUPER-DEBUG", "message": "Cerebro Patio API is running"}

