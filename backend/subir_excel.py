
import requests
import sys
import os
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

# Configuración
BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1" # RAILWAY PROD
ADMIN_EMAIL = "admin@cerebro.com"
ADMIN_PASS = "123456"

def load_env_vars():
    # Helper to load .env manually if needed
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    if k.strip() not in os.environ:
                        os.environ[k.strip()] = v.strip()

def send_local_email(ruta_excel, stats):
    print("\n--- Enviando Resumen por Email (Desde tu PC) ---")
    try:
        load_env_vars()
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASS")
        to_email = os.getenv("SMTP_TO", user)
        
        if not user or not password:
            print("⚠️ Credenciales SMTP no encontradas en .env local. Saltando email.")
            return

        df = pd.read_excel(ruta_excel)
        
        # Calculate Tech Stats
        tech_counts = {}
        if 'tecnico_nombre' in df.columns:
            tech_counts = df['tecnico_nombre'].value_counts().to_dict()

        msg = MIMEMultipart()
        msg['From'] = user
        msg['To'] = to_email
        msg['Subject'] = f"Resumen Planificación - {date.today()} (Local)"
        
        # Professional HTML Template
        html = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f7f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="background-color: #1a365d; color: white; padding: 30px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">REPORTE OPERATIVO DIARIO</h1>
                    <p style="margin: 5px 0 0; opacity: 0.9;">PLANIFICACIÓN | {date.today().strftime('%d-%m-%Y')}</p>
                </div>
                
                <div style="padding: 20px;">
                    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                        <div style="flex: 1; background: #e3f2fd; padding: 15px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 24px; font-weight: bold; color: #1565c0;">{stats.get('processed', 0)}</div>
                            <div style="font-size: 11px; font-weight: bold; color: #1565c0;">TOTAL TAREAS</div>
                        </div>
                        <div style="flex: 1; background: #e8f5e9; padding: 15px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 24px; font-weight: bold; color: #2e7d32;">{stats.get('created', 0)}</div>
                            <div style="font-size: 11px; font-weight: bold; color: #2e7d32;">NUEVAS</div>
                        </div>
                        <div style="flex: 1; background: #fff3e0; padding: 15px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 24px; font-weight: bold; color: #ef6c00;">{stats.get('updated', 0)}</div>
                            <div style="font-size: 11px; font-weight: bold; color: #ef6c00;">ACTUALIZADAS</div>
                        </div>
                    </div>

                    <h3 style="border-bottom: 2px solid #eee; padding-bottom: 10px; color: #333;">Detalle por Técnico</h3>
                    <table style="width: 100%; border-collapse: collapse;">
        """
        
        for tech, count in tech_counts.items():
            html += f"""
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;">{tech}</td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold; text-align: right;">{count}</td>
                        </tr>
            """
            
        html += """
                    </table>
                </div>
                <div style="background-color: #f8f9fa; padding: 15px; text-align: center; color: #888; font-size: 12px;">
                    Enviado desde PC Local (Script Seguro)
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        # Use Port 587 (TLS) - Proven to work locally
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        server.quit()
        print("✅ Email enviado exitosamente.")
        
    except Exception as e:
        print(f"⚠️ Error enviando email: {e}")

def subir_archivo(ruta_excel):
    if not os.path.exists(ruta_excel):
        print(f"Error: No se encuentra el archivo '{ruta_excel}'")
        return

    print(f"--- Iniciando Carga a {BASE_URL} ---")
    
    # 1. Obtener Token
    print("1. Autenticando...")
    try:
        login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASS})
        if login_res.status_code != 200:
            print(f"Error Login: {login_res.text}")
            return
        token = login_res.json()["access_token"]
    except Exception as e:
        print(f"Error de conexión: {e}")
        return

    # 2. Subir Archivo
    print(f"2. Subiendo archivo...")
    headers = {"Authorization": f"Bearer {token}"}
    stats = {}
    
    try:
        with open(ruta_excel, "rb") as f:
            files = {"file": (os.path.basename(ruta_excel), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            res = requests.post(f"{BASE_URL}/admin/upload_excel", headers=headers, files=files)
            
        if res.status_code == 200:
            data = res.json()
            stats = data.get("stats", {})
            print("✅ Carga Exitosa en Servidor.")
            print(f"   - Procesados: {stats.get('processed')}")
            print(f"   - Creados:    {stats.get('created')}")
            print(f"   - Actualiz.:  {stats.get('updated')}")
            
            # 3. TRIGGER LOCAL EMAIL
            send_local_email(ruta_excel, stats)
            
        else:
            print(f"❌ Error Servidor: {res.status_code} - {res.text}")
            
    except Exception as e:
        print(f"❌ Error en la solicitud: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python subir_excel.py <archivo.xlsx>")
    else:
        subir_archivo(sys.argv[1])
