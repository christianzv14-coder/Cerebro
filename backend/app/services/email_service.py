import os
import requests
from typing import List, Dict, Any
from datetime import date, datetime
from app.models.models import Activity

# Resend API Configuration
RESEND_API_URL = "https://api.resend.com/emails"

def _log_debug(msg):
    # Determine the log file path relative to the current working directory or a specific location
    # Ideally should be a persistent log or stdout in production
    # For now ensuring it doesn't fail on path issues
    try:
        with open("email_debug.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()}: {msg}\n")
    except Exception:
        print(f"DEBUG LOG ERROR: {msg}")

def _send_via_resend(to_email: str, subject: str, html_content: str):
    """
    Sends email using Resend API (HTTP).
    Bypasses SMTP port blocking.
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        _log_debug("WARNING: RESEND_API_KEY not set.")
        print("WARNING: RESEND_API_KEY not set. Email will not be sent.")
        raise Exception("Configuration Error: RESEND_API_KEY is missing.")

    # Sender must be verified in Resend. 
    # For testing: 'onboarding@resend.dev' works to the registered email.
    # For production: 'notificaciones@tudominio.com' (requires DNS setup)
    # We'll try to use a smart default or env var.
    sender = os.getenv("RESEND_FROM", "onboarding@resend.dev")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Resend Testing Mode: Use single email recipient
    # to_email should be a single verified email address
    to_emails = [to_email.strip()]
    
    _log_debug(f"Sending to: {to_emails}")
    
    payload = {
        "from": "Cerebro <" + sender + ">",
        "to": to_emails,
        "subject": subject,
        "html": html_content
    }

    _log_debug(f"Sending via Resend to {', '.join(to_emails)}...")
    
    try:
        resp = requests.post(RESEND_API_URL, json=payload, headers=headers)
        
        if resp.status_code in [200, 201, 202]:
            _log_debug(f"Resend Success: {resp.json()}")
            print(f"Email sent via Resend to {', '.join(to_emails)}")
            return True
        else:
            error_detail = resp.text
            _log_debug(f"Resend Failed: {resp.status_code} - {error_detail}")
            print(f"Resend Failed: {resp.status_code} - {error_detail}")
            raise Exception(f"Resend API Error: {resp.status_code} - {error_detail}")
            
    except Exception as e:
        _log_debug(f"Resend Exception: {e}")
        print(f"Resend Exception: {e}")
        raise e

def send_workday_summary(to_email: str, tech_name: str, workday_date: date, activities: List[Activity]):
    """
    Sends an email with the summary of the workday activities.
    """
    subject = f"✅ [INDIVIDUAL] Cierre de Jornada - {tech_name} - {workday_date}"

    # Calculate basic KPIs
    total = len(activities)
    completed = sum(1 for a in activities if a.estado.value == 'EXITOSO')
    failed = sum(1 for a in activities if a.estado.value == 'FALLIDO')
    
    # Colors
    c_primary = "#1a365d" # Dark Blue Header
    c_bg_light = "#f4f7f6"
    c_card_blue_text = "#1565c0"
    c_card_blue_bg = "#e3f2fd"
    c_card_green_text = "#2e7d32"
    c_card_green_bg = "#e8f5e9"
    c_card_red_text = "#c62828"
    c_card_red_bg = "#ffebee"

    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: {c_bg_light}; margin: 0; padding: 0; }}
            .container {{ max-width: 800px; margin: 0 auto; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-family: 'Segoe UI', sans-serif; }}
            .header {{ background-color: {c_primary}; color: white; padding: 30px 40px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }}
            .header p {{ margin: 10px 0 0; opacity: 0.8; font-size: 14px; }}
            
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
            .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #888; font-size: 12px; border-top: 1px solid #eee; }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <h1>Reporte de Cierre Diario</h1>
                <p>CONFIRMACIÓN DE JORNADA | {workday_date.strftime('%d-%m-%Y')}</p>
                <p style="font-size: 16px; margin-top: 5px;">Técnico: <strong>{tech_name}</strong></p>
            </div>
            
            <!-- Cards -->
            <table width="100%" cellpadding="0" cellspacing="10" style="padding: 10px;">
                <tr>
                    <td width="33%" style="background-color: {c_card_blue_bg}; border-radius: 8px; padding: 20px; text-align: center;">
                        <div class="kpi-number" style="color: {c_card_blue_text};">{total}</div>
                        <div class="kpi-label" style="color: {c_card_blue_text};">TOTAL TAREAS</div>
                    </td>
                    <td width="33%" style="background-color: {c_card_green_bg}; border-radius: 8px; padding: 20px; text-align: center;">
                        <div class="kpi-number" style="color: {c_card_green_text};">{completed}</div>
                        <div class="kpi-label" style="color: {c_card_green_text};">EXITOSAS</div>
                    </td>
                    <td width="33%" style="background-color: {c_card_red_bg}; border-radius: 8px; padding: 20px; text-align: center;">
                        <div class="kpi-number" style="color: {c_card_red_text};">{failed}</div>
                        <div class="kpi-label" style="color: {c_card_red_text};">FALLIDAS</div>
                    </td>
                </tr>
            </table>

            <div class="content">
                <div class="tech-section">
                    <div class="tech-header">
                        <span class="tech-name">Detalle de Actividades</span>
                    </div>
                    <table class="task-table">
                        <thead>
                            <tr>
                                <th width="15%">HORA</th>
                                <th width="25%">CLIENTE</th>
                                <th width="20%">TIPO</th>
                                <th width="20%">ESTADO</th>
                                <th width="20%">RESULTADO</th>
                            </tr>
                        </thead>
                        <tbody>
    """
    
    if not activities:
        html_content += "<tr><td colspan='5' style='text-align:center; padding:20px;'>No hay actividades registradas.</td></tr>"
    else:
        for act in activities:
            start = act.hora_inicio.strftime("%H:%M") if act.hora_inicio else "-"
            # end = act.hora_fin.strftime("%H:%M") if act.hora_fin else "-" # Not showing end time to save space
            reason = act.resultado_motivo if act.resultado_motivo else "-"
            
            # Status Color
            status_color = "#555"
            if act.estado.value == 'EXITOSO': status_color = "green"
            elif act.estado.value == 'FALLIDO': status_color = "red"
            
            html_content += f"""
            <tr>
                <td>{start}</td>
                <td>{act.cliente}</td>
                <td>{act.tipo_trabajo}</td>
                <td><span style="color: {status_color}; font-weight: bold;">{act.estado.value}</span></td>
                <td>{reason}</td>
            </tr>
            """

    html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="footer">
                <p>Generado automáticamente por CEREBRO SYSTEM</p>
                <p style="font-size: 10px; margin-top: 5px;">Enviado vía App API</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Send via Resend
    _send_via_resend(to_email, subject, html_content)


# Function kept for compatibility if needed, using generic implementation or similar logic
def send_plan_summary(stats: Dict[str, Any], df_data: Any, to_email: str = None):
    # Enabled again by user request (Single Report)
    pass
    
    # Original logic below disabled...
    _log_debug("--- Starting send_plan_summary ---")
    
    # Use override or Fallback to Env
    if not to_email:
        to_email = os.getenv("SMTP_TO", os.getenv("SMTP_USER")) # Legacy env var names
        
    _log_debug(f"Target Email: {to_email}")
    
    subject = f"Resumen Planificación - {date.today()}"

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
                <p>Enviado vía Resend API</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    _send_via_resend(to_email, subject, html_content)
