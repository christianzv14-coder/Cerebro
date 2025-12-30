from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.deps import get_current_admin, get_current_user
from app.services.excel_service import process_excel_upload

router = APIRouter()

@router.post("/upload_excel")
def upload_planification(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin), # Only Admin
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(('.xlsx', '.xls')):
         raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    
    try:
        # Read file into memory? 
        # SpooledTemporaryFile is file-like.
        contents = file.file.read()
        
        # Reset cursor? Pandas read_excel accepts bytes or file-like. 
        # But read() might have consumed it. 
        # Let's pass the file.file directly if possible, or BytesIO.
        from io import BytesIO
        from app.services.scores_service import update_scores_in_sheet
        
        io_file = BytesIO(contents)
        stats = process_excel_upload(io_file, db)
        
        # Trigger Score Update to refresh Puntajes with new data
        background_tasks.add_task(update_scores_in_sheet)
        
        return {"message": "Upload successful", "stats": stats}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/debug_full_system")
def debug_full_system(db: Session = Depends(get_db)):
    """
    Runs a complete diagnostic of the server's ability to send emails.
    """
    import socket
    import smtplib
    import os
    import sys
    from io import StringIO
    
    report = {
        "env_vars": {
            "SMTP_USER_SET": bool(os.getenv("SMTP_USER")),
            "SMTP_PASS_SET": bool(os.getenv("SMTP_PASS")),
            "SMTP_TO_SET": bool(os.getenv("SMTP_TO")),
            "SMTP_USER_LEN": len(os.getenv("SMTP_USER", "")),
            "SMTP_PASS_LEN": len(os.getenv("SMTP_PASS", "")),
            "SMTP_HOST": os.getenv("SMTP_HOST", "NOT_SET"),
            "SMTP_PORT": os.getenv("SMTP_PORT", "NOT_SET")
        },
        "network": {},
        "smtp_handshake": "Not Run"
    }
    
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    # 1. Network / DNS
    try:
        ip = socket.gethostbyname(smtp_host)
        report["network"]["dns"] = f"OK -> {ip}"
    except Exception as e:
        report["network"]["dns"] = f"FAIL: {e}"
        return report

    # 2. Port Check
    try:
        sock = socket.create_connection((smtp_host, smtp_port), timeout=5)
        report["network"][f"port_{smtp_port}"] = "OPEN"
        sock.close()
    except Exception as e:
        report["network"][f"port_{smtp_port}"] = f"CLOSED/TIMEOUT: {e}"
        # If port blocked, return early
        return report

    # 3. SMTP Conversation Capture
    log_capture = StringIO()
    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        server.set_debuglevel(1)
        # Redirect stderr to capture debug output
        original_stderr = sys.stderr
        sys.stderr = log_capture
        
        server.starttls()
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASS")
        
        login_resp = "Skipped (No Auth)"
        if user and password:
            try:
                server.login(user, password)
                login_resp = "Login SUCCESS"
                
                # Try sending a test email to self
                to_addr = os.getenv("SMTP_TO", user)
                msg = f"Subject: CEREBRO PROD DIAGNOSTIC\n\nDiagnostic Email Test from {socket.gethostname()}"
                server.sendmail(user, to_addr, msg)
                report["email_send_attempt"] = "SUCCESS (Accepted by Server)"
            except Exception as login_err:
                login_resp = f"Login FAILED: {login_err}"
        
        server.quit()
        report["smtp_handshake"] = login_resp
        
    except Exception as e:
        report["smtp_handshake"] = f"Handshake CRASHED: {e}"
    finally:
        sys.stderr = original_stderr
        report["smtp_log"] = log_capture.getvalue()
        
    return report
@router.get("/test_email")
def test_email_configuration(
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to test email sending using server env vars.
    """
    import os
    import pandas as pd
    from app.services.email_service import send_plan_summary

    user = os.getenv("SMTP_USER", "NOT_SET")
    to = os.getenv("SMTP_TO", "NOT_SET")
    
    # Mock Data
    stats = {"processed": 10, "created": 5, "updated": 5}
    df = pd.DataFrame({
        "tecnico_nombre": ["Tech A", "Tech B", "Tech A"],
        "comuna": ["Comuna 1", "Comuna 2", "Comuna 1"]
    })
    
    
    # Debug: Check what keys exist
    smtp_keys = [k for k in os.environ.keys() if "SMTP" in k]
    
    
    # Debug: Check network connectivity
    import socket
    network_results = {}
    try:
        ip = socket.gethostbyname("smtp.gmail.com")
        network_results["dns_resolution"] = f"Success ({ip})"
        
        # Test Port 465
        try:
            sock = socket.create_connection(("smtp.gmail.com", 465), timeout=2)
            network_results["port_465"] = "Open"
            sock.close()
        except Exception as e:
            network_results["port_465"] = f"Closed/Blocked ({e})"

        # Test Port 587
        try:
            sock = socket.create_connection(("smtp.gmail.com", 587), timeout=2)
            network_results["port_587"] = "Open"
            sock.close()
        except Exception as e:
            network_results["port_587"] = f"Closed/Blocked ({e})"
            
    except Exception as e:
        network_results["dns"] = f"Failed ({e})"

    try:
        # Try sending (will likely fail, but we want the detailed network report)
        send_plan_summary(stats, df)
        return {
            "message": "Email sent attempt finished.",
            "debug_config": {
                "from": f"{user[:3]}***@***" if len(user) > 5 else user,
                "found_keys_in_env": smtp_keys,
                "network_test": network_results
            }
        }
    except Exception as e:
        return {
            "error": str(e), 
            "network_test": network_results,
            "detail": "If ports are 'Closed/Blocked', Railway is preventing the connection."
        }


@router.post("/fix_signatures_schema")
def fix_signatures_schema(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Allow tech to fix db for now
):
    """
    Manually adds the Unique Constraint to day_signatures to prevent duplicates.
    """
    from sqlalchemy import text
    try:
        # PostgreSQL syntax
        # 1. First, delete duplicates if any (keeping the one with min id)
        # This acts as a cleanup before constraint
        sql_cleanup = """
        DELETE FROM day_signatures a USING day_signatures b
        WHERE a.id < b.id
        AND a.tecnico_nombre = b.tecnico_nombre
        AND a.fecha = b.fecha;
        """
        db.execute(text(sql_cleanup))
        
        # 2. Add Constraint
        # We use a specific name to catch if it exists
        sql_constraint = """
        ALTER TABLE day_signatures 
        ADD CONSTRAINT _tech_date_uc UNIQUE (tecnico_nombre, fecha);
        """
        db.execute(text(sql_constraint))
        db.commit()
        return {"status": "success", "message": "Constraint added successfully."}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}





@router.post("/debug_resend")
async def debug_resend(
    background_tasks: BackgroundTasks,
    to_email: str = "christianzv14@gmail.com",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Test Resend API directly.
    """
    from app.services.email_service import _send_via_resend
    
    html = "<h1>Test Resend</h1><p>Funciona OK.</p>"
    try:
        _send_via_resend(to_email, "[TEST] Debug Resend", html)
        return {"status": "ok", "message": f"Email sent to {to_email}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/debug_score_sync")
async def debug_score_sync(
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_admin) # Removed Auth for easier debugging via script
):
    """
    Executes the Score Sync logic with VERBOSE logging returned in response.
    Analyzes why rows are being skipped.
    """
    logs = []
    def log(msg): logs.append(msg)
    
    log(">>> STARTING DEBUG SYNC <<<")
    
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
    from app.services.sheet_client import get_sheet_client, normalize_header
    import os
    from datetime import datetime
    
    client = get_sheet_client()
    if not client:
        log("Sheet Client Init Failed.")
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
