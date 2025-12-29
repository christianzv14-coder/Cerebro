
import os
import sys
import pandas as pd
from datetime import date
from dotenv import load_dotenv

# Load env vars from .env file
load_dotenv()

# Add backend to path to allow imports
sys.path.append(os.getcwd())

try:
    from app.services.email_service import send_workday_summary
    from app.models.models import Activity, ActivityState
except ImportError:
    # Try alternate path if running from parent
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    from app.services.email_service import send_workday_summary
    from app.models.models import Activity, ActivityState

def test_workday_email():
    print("--- TESTING WORKDAY EMAIL ---")
    
    user_email = os.getenv("SMTP_TO") or os.getenv("SMTP_USER")
    print(f"Sending to: {user_email}")
    
    if not user_email:
        print("ERROR: No email address found in env vars (SMTP_TO or SMTP_USER)")
        return

    # Mock Data
    tech_name = "Técnico Pruebas"
    today = date.today()
    
    # Mock Activities
    from datetime import datetime
    
    activities = [
        Activity(
            ticket_id="TICKET-1",
            tecnico_nombre=tech_name, # Added mock tech name
            hora_inicio=datetime.now().replace(hour=9, minute=0),
            hora_fin=datetime.now().replace(hour=10, minute=30),
            cliente="Cliente A",
            tipo_trabajo="Instalación",
            estado=ActivityState.EXITOSO,
            resultado_motivo="OK"
        ),
        Activity(
            ticket_id="TICKET-2",
            tecnico_nombre=tech_name, # Added mock tech name
            hora_inicio=datetime.now().replace(hour=11, minute=0),
            hora_fin=datetime.now().replace(hour=12, minute=15),
            cliente="Cliente B",
            tipo_trabajo="Reparación",
            estado=ActivityState.FALLIDO,
            resultado_motivo="Cliente Ausente"
        )
    ]
    
    try:
        send_workday_summary(user_email, tech_name, today, activities)
        print("Email sent successfully!")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_workday_email()
