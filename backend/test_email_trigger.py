from subir_excel import send_local_email
import pandas as pd
import os

# Create dummy excel
df = pd.DataFrame([
    {"tecnico": "Test Tech", "actividad": "Test Job", "cliente": "Test Client"}
])
df.to_excel("test_upload_email.xlsx", index=False)

stats = {"processed": 1, "created": 1, "updated": 0}

print("Testing email trigger...")
try:
    send_local_email("test_upload_email.xlsx", stats)
    print("Test passed.")
except Exception as e:
    print(f"Test failed: {e}")
finally:
    if os.path.exists("test_upload_email.xlsx"):
        os.remove("test_upload_email.xlsx")
