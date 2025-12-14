# app.py
# Cerebro de Patio – Flask + OpenAI (API REST) + WhatsApp Cloud API (Meta)
# - Memoria persistente en BD (SQLite / Postgres)
# - Memoria por usuario (users + messages)
# - Filtro de tipo de mensaje y deduplicación
# - Listo para Railway (gunicorn)

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

if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en las variables de entorno")
if not WHATSAPP_TOKEN:
    raise RuntimeError("Falta WHATSAPP_TOKEN en las variables de entorno")
if not WHATSAPP_PHONE_ID:
    raise RuntimeError("Falta WHATSAPP_PHONE_ID en las variables de entorno")

# Base de datos:
# - En local: usa SQLite (cerebro.db)
# - En nube: define DATABASE_URL (ej: Postgres/Neon)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cerebro.db")

# Loguear qué BD se está usando y dónde está el archivo si es SQLite
if DATABASE_URL.startswith("sqlite:///"):
    db_file = DATABASE_URL.replace("sqlite:///", "", 1)
    db_abs_path = Path(db_file).resolve()
    print(">>> BASE DE DATOS USADA: SQLite")
    print(f">>> ARCHIVO BD: {db_abs_path}")
else:
    print(">>> BASE DE DATOS USADA por DATABASE_URL:")
    print(f">>> {DATABASE_URL}")

# =========================================================
# APP
# =========================================================
app = Flask(__name__)

# =========================================================
# CONFIGURACIÓN SQLALCHEMY
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
    name = Column(String(255), nullable=True)  # reservado para futuro


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(16))  # 'user' / 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="messages")


# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# Historial máximo por usuario (en mensajes, user+assistant)
MAX_HISTORY_MESSAGES = 20

# Set en RAM para deduplicar message_id de WhatsApp (evita duplicados por reintentos)
PROCESSED_MESSAGE_IDS = set()


# =========================================================
# BD helpers
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

        history = [{"role": m.role, "content": m.content} for m in msgs]
        if len(history) > MAX_HISTORY_MESSAGES:
            history = history[-MAX_HISTORY_MESSAGES:]
        return history


def append_message(phone: str, role: str, content: str):
    with get_db_session() as db:
        user = get_or_create_user_by_phone(db, phone)
        msg = Message(user_id=user.id, role=role, content=content)
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
# WhatsApp sender
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
        print("=== WhatsApp send ===", resp.status_code, resp.text)
    except Exception as e:
        print("Error enviando mensaje a WhatsApp:", repr(e))


# =========================================================
# OpenAI via REST (SIN SDK)
# =========================================================
def call_openai_chat(messages):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4.1-mini",
        "messages": messages,
        "temperature": 0.3,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        print("ERROR OpenAI:", resp.status_code, resp.text)
        raise RuntimeError(f"OpenAI error {resp.status_code}")

    data = resp.json()
    return data["choices"][0]["message"]["content"]


# =========================================================
# HEALTHCHECK / ROOT
# =========================================================
@app.route("/", methods=["GET"])
def healthcheck():
    return "Cerebro de Patio está corriendo (OpenAI via REST).", 200


# =========================================================
# WEBHOOK – VERIFICACIÓN (GET)
# =========================================================
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print("=== VERIFICACIÓN WEBHOOK ===", mode, token, challenge)

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return challenge, 200

    return "Token de verificación inválido", 403


# =========================================================
# WEBHOOK – MENSAJES (POST)
# =========================================================
@app.route("/webhook", methods=["POST"])
def receive_message():
    print("\n\n======================")
    print(">>> LLEGÓ UN POST A /webhook")
    print("Headers:", dict(request.headers))
    print("Raw body:", request.data)
    print("======================\n")

    # 1) Parse JSON
    try:
        data = request.get_json()
    except Exception as e:
        print("ERROR parseando JSON:", repr(e))
        return "ok", 200

    if not data:
        print("No vino JSON en el body")
        return "ok", 200

    # 2) Extraer mensaje y número
    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        messages = value.get("messages")
        if not messages:
            print("No hay 'messages' en el payload (probablemente status).")
            return "ok", 200

        message = messages[0]

        # Deduplicación por message_id (RAM)
        message_id = message.get("id")
        if message_id:
            if message_id in PROCESSED_MESSAGE_IDS:
                print(f"Mensaje {message_id} ya procesado. Ignorando.")
                return "ok", 200
            PROCESSED_MESSAGE_IDS.add(message_id)

        message_type = message.get("type")
        if message_type != "text":
            print(f"Mensaje ignorado: tipo '{message_type}' no soportado.")
            return "ok", 200

        from_number = message["from"]
        text_body = message.get("text", {}).get("body", "").strip()

        print(f"Mensaje desde {from_number}: {text_body}")

    except Exception as e:
        print("Error parseando estructura de WhatsApp:", repr(e))
        return "ok", 200

    if not text_body:
        print("Mensaje vacío. Ignorando.")
        return "ok", 200

    # 3) Reset de memoria (antes de OpenAI)
    lower_text = text_body.lower()
    if lower_text in ["reset", "reinicia", "reiniciar", "borrar memoria", "resetear memoria"]:
        reset_user_history(from_number)
        send_whatsapp_message(from_number, "Listo. Reseteé la memoria para este chat. Partimos de cero.")
        return "ok", 200

    # 4) Historial desde BD
    try:
        user_history = get_user_history(from_number)
    except Exception as e:
        print("ERROR en get_user_history:", repr(e))
        user_history = []

    # 5) System prompt maestro (ojo: removí el campo raro ".land")
    system_message = {
        "role": "system",
        "content": (
            "Eres 'Cerebro de Patio', un supervisor experto de patio en centros de "
            "distribución y crossdock de e-commerce en Chile. "
            "Respondes directo, sin rodeos, con foco operativo. "
            "Conoces conceptos como bloques de salida, andenes, flota tercerizada, "
            "conductores, rutas, SLAs, atrasos, mermas y seguridad en el patio. "
            "Hablas con Christian (subgerente de operaciones) y tus respuestas deben ser "
            "accionables en el piso: qué hacer, en qué orden y con quién. "
            "Si no tienes información suficiente, dilo y pide datos concretos."
        ),
    }

    messages_for_openai = [system_message] + user_history + [{"role": "user", "content": text_body}]

    # 6) Guardar SIEMPRE el mensaje del usuario ANTES de OpenAI
    try:
        append_message(from_number, "user", text_body)
    except Exception as e:
        print("ERROR guardando mensaje user:", repr(e))

    # 7) Llamar OpenAI (REST)
    try:
        reply = call_openai_chat(messages_for_openai)
        print("Respuesta OpenAI:", reply)

        try:
            append_message(from_number, "assistant", reply)
        except Exception as e:
            print("ERROR guardando mensaje assistant:", repr(e))

    except Exception as e:
        print("Error llamando a OpenAI:", repr(e))
        reply = "Tuve un problema hablando con el modelo. Intenta de nuevo en un momento."

    # 8) Enviar respuesta a WhatsApp
    send_whatsapp_message(from_number, reply)
    return "ok", 200


# =========================================================
# MAIN (solo local)
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
