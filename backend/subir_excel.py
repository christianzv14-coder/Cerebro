
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
        
        # 1. Identify Columns (Robust Search)
        headers = [c.lower().strip() for c in df.columns]
        col_map = {"tecnico": None, "actividad": None, "cliente": None}
        
        # Mapping variants
        variants = {
            "tecnico": ["tecnico_nombre", "tecnico", "técnico", "nombre tecnico"],
            "actividad": ["tipo_trabajo", "actividad", "tipo trabajo", "tarea"],
            "cliente": ["cliente", "nombre_cliente", "client"]
        }
        
        for key, possible_names in variants.items():
            for name in possible_names:
                if name in headers:
                    # Find original casing
                    col_map[key] = df.columns[headers.index(name)]
                    break
        
        # 2. Build Data Structure
        tech_data = {} # { "Juan": [ {"actividad": "...", "cliente": "..."}, ... ] }
        
        if col_map["tecnico"]:
            # Fill NaN with empty strings to avoid errors
            df = df.fillna("")
            
            for index, row in df.iterrows():
                tech = str(row[col_map["tecnico"]]).strip()
                if not tech: continue
                
                act = row[col_map["actividad"]] if col_map["actividad"] else "N/A"
                cli = row[col_map["cliente"]] if col_map["cliente"] else "N/A"
                
                if tech not in tech_data:
                    tech_data[tech] = []
                
                tech_data[tech].append({"actividad": act, "cliente": cli})

        msg = MIMEMultipart()
        msg['From'] = user
        msg['To'] = to_email
        msg['Subject'] = f"Resumen Planificación - {date.today()} (Local)"
        
        # 3. Build HTML
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
                    </div>

                    <h3 style="border-bottom: 2px solid #eee; padding-bottom: 10px; color: #333;">Detalle por Técnico</h3>
        """
        
        if not tech_data:
            html += "<p style='color: #666;'>No se encontraron técnicos en el archivo.</p>"
        else:
            for tech, activities in tech_data.items():
                html += f"""
                    <div style="margin-bottom: 20px;">
                        <div style="background-color: #f8f9fa; padding: 10px; border-left: 4px solid #1a365d; font-weight: bold; color: #2c3e50;">
                            {tech} <span style="font-weight: normal; font-size: 12px; color: #666;">({len(activities)} tareas)</span>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; margin-top: 5px; font-size: 13px;">
                            <tr style="background-color: #eee; color: #555;">
                                <th style="padding: 8px; text-align: left; border-bottom: 1px solid #ddd;">Actividad</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 1px solid #ddd;">Cliente</th>
                            </tr>
                """
                for item in activities:
                    html += f"""
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #eee;">{item['actividad']}</td>
                                <td style="padding: 8px; border-bottom: 1px solid #eee; color: #555;">{item['cliente']}</td>
                            </tr>
                    """
                html += "</table></div>"
            
        html += """
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
        print("✅ Email detallado enviado exitosamente.")
        
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
