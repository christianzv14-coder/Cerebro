from fastapi import FastAPI
import os
from app.core.config import settings
from app.database import engine, Base
from fastapi.staticfiles import StaticFiles
from app.routers import auth, users, activities, admin, signatures, finance
from app.models.finance import Expense  # Import to register with Base

# Create tables on startup (simple for MVP)
Base.metadata.create_all(bind=engine)

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
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])

@app.get("/")
def root():
    return {"status": "online", "version": "3.1-EMERGENCY-DEBUG", "message": "Cerebro Patio API is running"}

# --- EMERGENCY DEBUG ENDPOINT ---
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db

@app.get("/debug_score_sync_direct")
async def debug_score_sync_direct(db: Session = Depends(get_db)):
    """
    Direct debug endpoint in Main.py to bypass router issues.
    """
    logs = []
    def log(msg): logs.append(msg)
    log(">>> STARTING DIRECT DEBUG SYNC <<<")

    # 1. Fetch Signatures
    from app.models.models import DaySignature
    signed_days = set()
    try:
        sigs = db.query(DaySignature).filter(DaySignature.is_signed == True).all()
        for s in sigs:
            signed_days.add((str(s.fecha), str(s.tecnico_nombre).strip().upper()))
            log(f"DB Signature Found: Key={str(s.fecha)}, {str(s.tecnico_nombre).strip().upper()}")
    except Exception as e:
        log(f"DB Error: {e}")
        return {"logs": logs}
        
    log(f"Total Signatures in DB: {len(signed_days)}")
    
    # 2. Read Sheet
    from app.services.sheets_service import get_sheet
    import os
    from datetime import datetime
    
    def normalize_header(h):
        return str(h).strip().lower()
    
    # Use get_sheet instead of get_sheet_client
    try:
        sheet = get_sheet()
    except Exception as e:
         log(f"Get Sheet Failed: {e}")
         return {"logs": logs}
         
    if not sheet:
        log("Sheet Client Init Failed (returned None).")
        return {"logs": logs}
        
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    try:
        sheet = client.open_by_key(sheet_id)
        current_year = datetime.now().year
        ws = sheet.worksheet(f"Bitacora {current_year}")
        all_values = ws.get_all_values()
        log(f"Read Bitacora: {len(all_values)} rows.")
    except Exception as e:
        log(f"Sheet Read Error: {e}")
        try:
             ws = sheet.worksheet("Bitacora")
             all_values = ws.get_all_values()
             log(f"Fallback to 'Bitacora' (No Year): {len(all_values)} rows.")
        except:
             return {"logs": logs}
        
    headers = [normalize_header(h) for h in all_values[0]]
    log(f"Headers: {headers}")
    
    try:
        idx_tecnico = headers.index("tecnico")
        idx_fecha = headers.index("fecha plan")
    except:
        log("Missing headers.")
        return {"logs": logs}
        
    # 3. Analyze Rows
    match_count = 0
    
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) <= idx_tecnico: continue
        
        raw_tech = row[idx_tecnico]
        raw_date = row[idx_fecha]
        
        tecnico = str(raw_tech).strip().upper()
        fecha_str = str(raw_date).strip()
        
        # Parse Date
        parsed_iso = None
        if not fecha_str:
             pass
        elif '-' in fecha_str:
             parts = fecha_str.split('-')
             if len(parts[0]) == 4: 
                 parsed_iso = parts[0] + "-" + parts[1] + "-" + parts[2]
             else: 
                 parsed_iso = parts[2] + "-" + parts[1] + "-" + parts[0]
        elif '/' in fecha_str:
             parts = fecha_str.split('/')
             parsed_iso = parts[2] + "-" + parts[1] + "-" + parts[0]
             
        key = (parsed_iso, tecnico)
        is_signed = key in signed_days
        
        if is_signed:
            match_count += 1
            log(f"Row {i} MATCH! Tech='{tecnico}' Date='{parsed_iso}'")
        else:
            if i < 7:
                 log(f"Row {i} FAIL. Tech='{tecnico}' Date='{parsed_iso}' (Raw: {fecha_str}) NOT IN DB.")
                 
    log(f"Total Matches: {match_count}")
    return {"logs": logs}

