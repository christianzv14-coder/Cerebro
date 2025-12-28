import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
import pandas as pd

# Configuration from Environment Variables
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # SSL Port

# ... (omitted)

        # 4. Send
        print(f"Connecting to SMTP_SSL {SMTP_SERVER}...")
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        # server.starttls()  <-- Not needed for SSL connection
        server.login(SMTP_USER, SMTP_PASS)
        text = msg.as_string()
        server.sendmail(SMTP_USER, SMTP_TO, text)
        server.quit()
        
        print(f"Email sent successfully to {SMTP_TO}")

    except Exception as e:
        print(f"ERROR sending email: {e}")
        raise e  # Re-raise so the caller/endpoint sees the error!
