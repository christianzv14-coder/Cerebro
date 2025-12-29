
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any
from datetime import date, datetime
from app.models.models import Activity

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def _log_debug(msg):
    with open("email_debug.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()}: {msg}\n")

def _get_smtp_connection():
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    
    _log_debug(f"Connecting to SMTP as {user}...")
    
    if not user or not password:
        _log_debug("WARNING: SMTP credentials not set.")
        print("WARNING: SMTP credentials not set. Email will not be sent.")
        return None
        
    try:
        # Use simple SMTP with STARTTLS for Port 587
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.starttls()
        server.login(user, password)
        _log_debug("SMTP Login Success")
        return server
    except Exception as e:
        _log_debug(f"SMTP Connection Error: {e}")
        print(f"SMTP Connection Error: {e}")
        return None

def send_workday_summary(to_email: str, tech_name: str, workday_date: date, activities: List[Activity]):
    """
    Sends an email with the summary of the workday activities.
    """
    server = _get_smtp_connection()
    if not server:
        return

    msg = MIMEMultipart()
    msg['From'] = os.getenv("SMTP_USER")
    msg['To'] = to_email
    msg['Subject'] = f"Resumen Jornada Laboral - {tech_name} - {workday_date}"

    # Generate HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
            th {{ background-color: #f2f2f2; }}
            .header {{ font-family: Arial, sans-serif; }}
        </style>
    </head>
    <body class="header">
        <h2>Confirmación de Jornada Laboral</h2>
        <p><strong>Técnico:</strong> {tech_name}</p>
        <p><strong>Fecha:</strong> {workday_date}</p>
        <p>Se ha registrado exitosamente su firma para la jornada.</p>
        
        <h3>Detalle de Actividades</h3>
        <table>
            <tr>
                <th>Técnico</th>
                <th>Hora Inicio</th>
                <th>Hora Fin</th>
                <th>Cliente</th>
                <th>Tipo Trabajo</th>
                <th>Estado</th>
                <th>Resultado</th>
            </tr>
    """
    
    if not activities:
        html_content += "<tr><td colspan='7'>No hay actividades registradas para este día.</td></tr>"
    else:
        for act in activities:
            start = act.hora_inicio.strftime("%H:%M") if act.hora_inicio else "-"
            end = act.hora_fin.strftime("%H:%M") if act.hora_fin else "-"
            reason = act.resultado_motivo if act.resultado_motivo else "-"
            # Fallback if tecnico_nombre is not on the object (e.g. legacy or mock), though it should be.
            # actually tech_name is passed to the function, so we can use that if act.tecnico_nombre is missing?
            # But Activity model has tecnico_nombre. Let's use act.tecnico_nombre if valid, else tech_name.
            t_name = getattr(act, 'tecnico_nombre', tech_name)
            
            html_content += f"""
            <tr>
                <td>{t_name}</td>
                <td>{start}</td>
                <td>{end}</td>
                <td>{act.cliente}</td>
                <td>{act.tipo_trabajo}</td>
                <td>{act.estado.value}</td>
                <td>{reason}</td>
            </tr>
            """

    html_content += """
        </table>
        <br>
        <p>Este correo ha sido generado automáticamente por el sistema Cerebro.</p>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_content, 'html'))

    try:
        server.send_message(msg)
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()

# Function kept for compatibility if needed, using generic implementation or similar logic
def send_plan_summary(stats: Dict[str, Any], df_data: Any):
    _log_debug("--- Starting send_plan_summary ---")
    
    # Retrieve necessary data or just log for now if not immediately needed
    server = _get_smtp_connection()
    if not server:
        _log_debug("Aborting send_plan_summary: No SMTP Server")
        return

    to_email = os.getenv("SMTP_TO", os.getenv("SMTP_USER"))
    _log_debug(f"Target Email: {to_email}")
    
    msg = MIMEMultipart()
    msg['From'] = os.getenv("SMTP_USER")
    msg['To'] = to_email
    msg['Subject'] = f"Resumen Planificación - {date.today()}"

    # Generate Stats
    # Assuming df_data is a DataFrame
    
    if hasattr(df_data, 'groupby'):
        try:
             # Calculate per-technician, per-commune stats
             tech_counts = df_data['tecnico_nombre'].value_counts().to_dict()
             comuna_counts = df_data.get('Comuna', df_data.get('comuna')).value_counts().to_dict() if 'Comuna' in df_data.columns or 'comuna' in df_data.columns else {}
             _log_debug(f"Stats calculated: {len(tech_counts)} techs, {len(comuna_counts)} comunas")
        except Exception as e:
            _log_debug(f"Warning computing stats: {e}")
            print(f"Warning computing stats: {e}")
            tech_counts = {}
            comuna_counts = {}
    else:
        _log_debug("df_data has no groupby/stats capability")
        tech_counts = {}
        comuna_counts = {}

    # --- PROFESSIONAL TEMPLATE GENERATION ---

    # 1. Prepare Data Grouped by Technician
    # Data structure: { "Juan Perez": [ {row_dict}, ... ], ... }
    grouped_tasks = {}
    if hasattr(df_data, 'to_dict'):
        records = df_data.to_dict(orient='records')
        for row in records:
            # Handle potential different column names if case changed
            tech = str(row.get('tecnico_nombre', 'Sin Asignar')).strip()
            if tech not in grouped_tasks:
                grouped_tasks[tech] = []
            grouped_tasks[tech].append(row)
    
    # 2. HTML Helper Styles
    # Using inline CSS for email compatibility
    
    # Colors
    c_primary = "#1a365d" # Dark Blue Header
    c_bg_light = "#f8f9fa"
    c_card_blue_bg = "#e3f2fd"
    c_card_blue_text = "#1976d2"
    c_card_green_bg = "#e8f5e9" 
    c_card_green_text = "#2e7d32"
    c_card_yellow_bg = "#fffde7"
    c_card_yellow_text = "#f57f17"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background-color: #ffffff; }}
            .header {{ background-color: {c_primary}; color: #ffffff; padding: 30px; text-align: left; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: 600; }}
            .header p {{ margin: 5px 0 0 0; font-size: 14px; opacity: 0.8; text-transform: uppercase; letter-spacing: 1px; }}
            
            .kpi-container {{ display: flex; padding: 20px; gap: 15px; justify-content: space-between; }}
            .kpi-card {{ flex: 1; padding: 20px; border-radius: 8px; text-align: center; }}
            .kpi-number {{ font-size: 32px; font-weight: bold; margin: 0; }}
            .kpi-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-top: 5px; font-weight: 600; }}
            
            .content {{ padding: 20px; }}
            .tech-section {{ margin-bottom: 30px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }}
            .tech-header {{ background-color: #f1f5f9; padding: 15px; border-bottom: 1px solid #e0e0e0; display: flex; align-items: center; }}
            .tech-name {{ font-weight: 700; color: #333; font-size: 16px; margin-right: 10px; }}
            .tech-badge {{ background-color: #1976d2; color: white; border-radius: 12px; padding: 2px 10px; font-size: 12px; font-weight: 600; }}
            
            .task-table {{ width: 100%; border-collapse: collapse; }}
            .task-table th {{ text-align: left; padding: 12px; color: #888; font-size: 12px; font-weight: 600; border-bottom: 1px solid #eee; }}
            .task-table td {{ padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; color: #444; vertical-align: top; }}
            .task-table tr:last-child td {{ border-bottom: none; }}
            
            .ticket-id {{ font-weight: 600; color: #1a365d; }}
            .tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; background-color: #eee; color: #555; }}
            
            .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #888; font-size: 12px; border-top: 1px solid #eee; }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <h1>Reporte Operativo Diario</h1>
                <p>CEREBRO PLANIFICACIÓN | {date.today().strftime('%A, %d de %B de %Y')}</p>
            </div>
            
            <!-- Cards (Using Tables for Email Compatibility instead of Flex) -->
            <table width="100%" cellpadding="0" cellspacing="10" style="padding: 10px;">
                <tr>
                    <td width="33%" style="background-color: {c_card_blue_bg}; border-radius: 8px; padding: 20px; text-align: center;">
                        <div class="kpi-number" style="color: {c_card_blue_text};">{stats.get('processed', 0)}</div>
                        <div class="kpi-label" style="color: {c_card_blue_text};">TOTAL TAREAS</div>
                    </td>
                    <td width="33%" style="background-color: {c_card_green_bg}; border-radius: 8px; padding: 20px; text-align: center;">
                        <div class="kpi-number" style="color: {c_card_green_text};">{stats.get('created', 0)}</div>
                        <div class="kpi-label" style="color: {c_card_green_text};">NUEVAS</div>
                    </td>
                    <td width="33%" style="background-color: {c_card_yellow_bg}; border-radius: 8px; padding: 20px; text-align: center;">
                        <div class="kpi-number" style="color: {c_card_yellow_text};">{stats.get('updated', 0)}</div>
                        <div class="kpi-label" style="color: {c_card_yellow_text};">ACTUALIZADAS</div>
                    </td>
                </tr>
            </table>

            <div class="content">
                <h3 style="color: #333; margin-top:0;">Detalle de Asignaciones</h3>
    """
    
    # Loop Technicians
    for tech, tasks in grouped_tasks.items():
        task_count = len(tasks)
        html_content += f"""
                <div class="tech-section">
                    <div class="tech-header">
                        <span class="tech-name">{tech}</span>
                        <span class="tech-badge">{task_count} Tareas</span>
                    </div>
                    <table class="task-table">
                        <thead>
                            <tr>
                                <th width="20%">TICKET</th>
                                <th width="25%">CLIENTE</th>
                                <th width="20%">TIPO</th>
                                <th width="20%">DIRECCIÓN</th>
                                <th width="15%">COMUNA</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        for t in tasks:
            # Safe get
            tid = t.get('ticket_id', '-')
            cli = t.get('cliente', '-')
            tipo = t.get('tipo_trabajo', '-')
            dire = t.get('direccion', '-')
            com = t.get('Comuna', t.get('comuna', '-'))
            
            html_content += f"""
                            <tr>
                                <td><span class="ticket-id">{tid}</span></td>
                                <td>{cli}</td>
                                <td>{tipo}</td>
                                <td>{dire}</td>
                                <td><span class="tag">{com}</span></td>
                            </tr>
            """
        html_content += """
                        </tbody>
                    </table>
                </div>
        """

    html_content += f"""
            </div>
            
            <div class="footer">
                <p>Generado automáticamente por CEREBRO SYSTEM © {date.today().year}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        server.send_message(msg)
        _log_debug(f"Plan Summary Email sent successfully to {to_email}")
        print(f"Plan Summary Email sent successfully to {to_email}")
    except Exception as e:
        _log_debug(f"Failed to send email: {e}")
        print(f"Failed to send email: {e}")
    finally:
        server.quit()
