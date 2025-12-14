# app.py
# Cerebro de Patio – Flask + OpenAI + WhatsApp Cloud API (Meta)
# - Memoria persistente en BD (SQLite local / Postgres en nube)
# - Deduplicación por message_id en BD (no RAM)
# - Soporta status updates (los ignora)
# - Healthcheck + ping
#
# IMPORTANTE (Railway):
# - En requirements.txt fija compatibilidad para evitar el error "proxies":
#     openai==1.40.6
#     httpx==0.27.2
#   Si no fijas httpx, pip puede instalar una versión incompatible y se cae.
#
# Procfile típico:
#   web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120

import os
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, request
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# =========================================================
# CARGA DE VARIABLES DE ENTORNO
# =========================================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "cerebro_token_123")

if not WHATSAPP_TOKEN:
    raise RuntimeError("Falta WHATSAPP_TOKEN en las variables de entorno")
if not WHATSAPP_PHONE_ID:
    raise RuntimeError("Falta WHATSAPP_PHONE_ID en las variables de entorno")

# Base de datos:
# - Local: sqlite:///cerebro.db
# - Nube: setea DATABASE_URL (Postgres)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cerebro.db")

# Log BD usada
if DATABASE_URL.startswith("sqlite:///"):
    db_file = DATABASE_URL.replace("sqlite:///", "", 1)
    db_abs_path = Path(db_file).resolve()
    print(">>> BASE DE DATOS USADA: SQLite")
    print(f">>> ARCHIVO BD: {db_abs_path}")
else:
    print(">>> BASE DE DATOS USADA por DATABASE_URL:")
    print(f">>> {DATABASE_URL}")

# =========================================================
# FLASK
# =========================================================
app = Flask(__name__)

# =========================================================
# SQLALCHEMY
# =========================================================
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    phone = Column(String(32), unique=True, index=True)
    name = Column(String(255), nullable=True)  # reservado


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(16))  # 'user' / 'assistant' / 'system'
    content = Column(Text, nullable=True)
    wa_message_id = Column(String(128), nullable=True)  # para dedupe (solo WhatsApp)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="messages")

    __table_args__ = (
        UniqueConstraint("wa_message_id", name="uq_messages_wa_message_id"),
    )


Base.metadata.create_all(bind=engine)

MAX_HISTORY_MESSAGES = 20


# =========================================================
# DB HELPERS
# =========================================================
def get_db_session():
    return SessionLocal()


def get_or_create_user_by_phone(db, phone: str) -> User:
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def was_message_id_processed(db, wa_message_id: str) -> bool:
    if not wa_message_id:
        return False
    exists = db.query(Message).filter(Message.wa_message_id == wa_message_id).first()
    return exists is not None


def get_user_history(phone: str):
    with get_db_session() as db:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return []

        msgs = (
            db.query(Message)
            .filter(Message.user_id == user.id)
            .order_by(Message.created_at.asc())
            .all()
        )

        # Solo roles válidos para OpenAI
        history = [{"role": m.role, "content": m.content} for m in msgs if m.role in ("user", "assistant")]
        if len(history) > MAX_HISTORY_MESSAGES:
            history = history[-MAX_HISTORY_MESSAGES:]
        return history


def append_message(phone: str, role: str, content: str, wa_message_id: str = None):
    with get_db_session() as db:
        user = get_or_create_user_by_phone(db, phone)
        msg = Message(user_id=user.id, role=role, content=content, wa_message_id=wa_message_id)
        db.add(msg)
        db.commit()


def reset_user_history(phone: str):
    with get_db_session() as db:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return
        db.query(Message).filter(Message.user_id == user.id).delete()
        db.commit()


# =========================================================
# WHATSAPP SEND
# =========================================================
def send_whatsapp_message(to_number: str, text: str):
    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        print("=== WHATSAPP SEND ===", resp.status_code, resp.text)
    except Exception as e:
        print("Error enviando mensaje a WhatsApp:", repr(e))


# =========================================================
# OPENAI (lazy init para que NO caiga el worker al boot)
# =========================================================
_openai_client = None


def get_openai_client():
    """
    Lazy init: evita que Gunicorn se caiga al importar si hay incompatibilidad de libs.
    Si esto falla con 'proxies', es requirements (openai/httpx), no código.
    """
    global _openai_client

    if _openai_client is not None:
        return _openai_client

    if not OPENAI_API_KEY:
        raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno")

    from openai import OpenAI  # import aquí (no arriba) para aislar crash en runtime

    _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


# =========================================================
# ROUTES
# =========================================================
@app.route("/", methods=["GET"])
def healthcheck():
    return "Cerebro de Patio está corriendo.", 200


@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200


@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print("=== VERIFICACIÓN WEBHOOK ===", {"mode": mode, "token": token, "challenge": challenge})

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return challenge, 200

    return "Token de verificación inválido", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    print("\n\n======================")
    print(">>> LLEGÓ UN POST A /webhook")
    print("Headers:", dict(request.headers))
    print("Raw body:", request.data)
    print("======================\n")

    # Parse JSON
    try:
        data = request.get_json(silent=True)
        print("=== JSON PARSEADO ===")
        print(data)
    except Exception as e:
        print("ERROR parseando JSON:", repr(e))
        return "ok", 200

    if not data:
        return "ok", 200

    # Extraer estructura
    try:
        entry = data.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})

        # Si viene status update, ignorar
        if value.get("statuses") and not value.get("messages"):
            print("Evento de status (no mensaje). Ignorando.")
            return "ok", 200

        messages = value.get("messages")
        if not messages:
            print("No hay 'messages' en payload.")
            return "ok", 200

        message = messages[0]
        wa_message_id = message.get("id")
        from_number = message.get("from")
        message_type = message.get("type")

        if message_type != "text":
            print(f"Mensaje ignorado: tipo '{message_type}' no soportado.")
            return "ok", 200

        text_body = (message.get("text", {}) or {}).get("body", "")
        text_body = text_body.strip()

        if not from_number:
            print("No vino 'from' en el payload.")
            return "ok", 200

    except Exception as e:
        print("Error parseando estructura de WhatsApp:", repr(e))
        return "ok", 200

    # Deduplicación en BD
    with get_db_session() as db:
        if wa_message_id and was_message_id_processed(db, wa_message_id):
            print(f"Mensaje {wa_message_id} ya procesado (BD). Ignorando.")
            return "ok", 200

    print(f"Mensaje desde {from_number}: {text_body} (id={wa_message_id})")

    # Reset memoria
    lower_text = text_body.lower()
    if lower_text in ["reset", "reinicia", "reiniciar", "borrar memoria", "resetear memoria"]:
        reset_user_history(from_number)
        send_whatsapp_message(from_number, "Listo. Reseteé la memoria para este chat. Partimos de cero.")
        # Guardar evento (opcional)
        append_message(from_number, "user", text_body, wa_message_id=wa_message_id)
        append_message(from_number, "assistant", "Memoria reseteada.", wa_message_id=None)
        return "ok", 200

    # Historial + system prompt
    try:
        user_history = get_user_history(from_number)
    except Exception as e:
        print("ERROR en get_user_history:", repr(e))
        user_history = []

    system_message = {
        "role": "system",
        "content": (
            "Eres 'Cerebro de Patio', un supervisor experto de patio en centros de "
            "distribución y crossdock de e-commerce en Chile. Respondes directo, "
            "sin rodeos, con foco operativo. Conoces conceptos como bloques de salida, "
            "andenes, flota tercerizada, conductores, rutas, SLAs, atrasos, mermas y "
            "seguridad en el patio. Hablas con Christian (subgerente de operaciones) "
            "y tus respuestas deben ser accionables: qué hacer, en qué orden y con quién. "
            "Si falta información, pide los datos mínimos."
        ),
    }

    messages_for_openai = [system_message] + user_history + [{"role": "user", "content": text_body}]

    # Guardar SIEMPRE el mensaje del usuario ANTES de OpenAI (con wa_message_id para dedupe)
    append_message(from_number, "user", text_body, wa_message_id=wa_message_id)

    # Llamar OpenAI
    try:
        client = get_openai_client()
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages_for_openai,
        )
        reply = completion.choices[0].message.content or ""
        reply = reply.strip() if reply else ""
        if not reply:
            reply = "Recibido. Dame un poco más de contexto (bloque, cantidad de rutas, y restricción principal)."

        append_message(from_number, "assistant", reply)

    except Exception as e:
        print("Error llamando a OpenAI:", repr(e))
        reply = (
            "Estoy arriba, pero se cayó la capa de IA por dependencias/credenciales. "
            "Revisa OPENAI_API_KEY y fija httpx compatible (ej: httpx==0.27.2)."
        )

    send_whatsapp_message(from_number, reply)
    return "ok", 200


# =========================================================
# MAIN (solo local)
# =========================================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
