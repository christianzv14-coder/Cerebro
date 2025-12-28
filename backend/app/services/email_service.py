# -*- coding: utf-8 -*-
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
import pandas as pd

# Configuration from Environment Variables
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # SSL Port
SMTP_USER = os.getenv("SMTP_USER")      # Sender Email
SMTP_PASS = os.getenv("SMTP_PASS")      # App Password
SMTP_TO = os.getenv("SMTP_TO")          # Recipient Email

def send_plan_summary(stats: dict, df: pd.DataFrame):
    """
    Sends an HTML email with the summary of the uploaded plan.
    """
    if not SMTP_USER or not SMTP_PASS or not SMTP_TO:
        print("WARNING: Email configuration missing. Skipping email.")
        return

    try:
        # 1. Prepare Data for Email
        total_tasks = stats.get('created', 0) + stats.get('updated', 0)
        upload_date = date.today().strftime("%d-%m-%Y")
        
        # Calculate breakdown by Comuna
        comuna_html = ""
        if 'comuna' in df.columns:
            # Group by Comuna and count
            counts = df['comuna'].value_counts()
            rows = ""
            for comuna, count in counts.items():
                rows += f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>{comuna}</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>{count}</td></tr>"
            
            comuna_html = f"""
            <h3>Desglose por Comuna</h3>
            <table style='border-collapse: collapse; width: 100%; max-width: 400px;'>
                <tr style='background-color: #f2f2f2;'>
                    <th style='padding: 8px; border: 1px solid #ddd; text-align: left;'>Comuna</th>
                    <th style='padding: 8px; border: 1px solid #ddd; text-align: center;'>Tareas</th>
                </tr>
                {rows}
            </table>
            """

        # Calculate breakdown by Technician
        tech_html = ""
        if 'tecnico_nombre' in df.columns:
            counts = df['tecnico_nombre'].value_counts()
            rows = ""
            for tech, count in counts.items():
                rows += f"<tr><td style='padding: 8px; border: 1px solid #ddd;'>{tech}</td><td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>{count}</td></tr>"
            
            tech_html = f"""
            <h3>Desglose por Técnico</h3>
            <table style='border-collapse: collapse; width: 100%; max-width: 400px;'>
                <tr style='background-color: #f2f2f2;'>
                    <th style='padding: 8px; border: 1px solid #ddd; text-align: left;'>Técnico</th>
                    <th style='padding: 8px; border: 1px solid #ddd; text-align: center;'>Asignaciones</th>
                </tr>
                {rows}
            </table>
            """

        # 2. Build HTML Body
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #2c3e50;">Resumen de Planificación Cargada</h2>
            <p><strong>Fecha de Carga:</strong> {upload_date}</p>
            
            <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                <p style="margin: 5px 0;"><strong>Total Procesado:</strong> {stats.get('processed', 0)} registros</p>
                <p style="margin: 5px 0;"><strong>Nuevas Tareas:</strong> {stats.get('created', 0)}</p>
                <p style="margin: 5px 0;"><strong>Actualizadas:</strong> {stats.get('updated', 0)}</p>
            </div>

            {comuna_html}
            <br>
            {tech_html}

            <p style="margin-top: 30px; font-size: 12px; color: #777;">
                Este es un mensaje automático del sistema CEREBRO.
            </p>
        </body>
        </html>
        """

        # 3. Setup Message
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = SMTP_TO
        msg['Subject'] = f"Resumen Planificación CEREBRO - {upload_date}"
        
        msg.attach(MIMEText(html_content, 'html'))

        # 4. Send via SMTP_SSL (Port 465)
        print(f"Connecting to SMTP_SSL {SMTP_SERVER}...")
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USER, SMTP_PASS)
        text = msg.as_string()
        server.sendmail(SMTP_USER, SMTP_TO, text)
        server.quit()
        
        print(f"Email sent successfully to {SMTP_TO}")

    except Exception as e:
        print(f"ERROR sending email: {e}")
        raise e
