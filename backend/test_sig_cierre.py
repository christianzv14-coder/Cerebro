import sys
import os
sys.path.append(os.getcwd())
from app.models.models import DaySignature
from app.services.sheets_service import sync_signature_to_sheet
from datetime import date, datetime

def test_sig_sync():
    print("--- TESTING SIGNATURE SYNC -> FECHA CIERRE ---")
    
    # Create a dummy signature object
    sig = DaySignature(
        tecnico_nombre="Juan Perez",
        fecha=date.today(),
        signature_ref="test_ref.png",
        timestamp=datetime.now()
    )
    
    try:
        print(f"Syncing signature for {sig.tecnico_nombre} at {sig.timestamp}...")
        sync_signature_to_sheet(sig)
        print("\nSUCCESS: 'Fecha Cierre' and 'Firmado' should be updated in Google Sheets.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_sig_sync()
