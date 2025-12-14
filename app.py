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


# from flask import Response

# =========================================================
# WEBHOOK – VERIFICACIÓN (GET)  ✅ META COMPATIBLE
# =========================================================
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode", "")
    token = request.args.get("hub.verify_token", "")
    challenge = request.args.get("hub.challenge", "")

    print("=== VERIFICACIÓN WEBHOOK ===")
    print("mode:", mode)
    print("token:", token)
    print("challenge:", challenge)

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN and challenge:
        return Response(challenge, status=200, mimetype="text/plain")

    return Response("Token de verificación inválido", status=403, mimetype="text/plain")


# =========================================================
# WEBHOOK – MENSAJES (POST)
# =========================================================
PROCESSED_MESSAGE_IDS = []
PROCESSED_MESSAGE_IDS_SET = set()
MAX_DEDUP = 2000


@app.route("/webhook", methods=["POST"])
def receive_message():
    print("\n======================")
    print(">>> LLEGÓ UN POST A /webhook")
    print("Headers:", dict(request.headers))
    print("Raw body:", request.data)
    print("======================")

    # 1) Parse JSON
    try:
        data = request.get_json()
    except Exception as e:
        print("ERROR parseando JSON:", repr(e))
        return "ok", 200

    if not data:
        print("No vino JSON")
        return "ok", 200

    # 2) Extraer mensaje
    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        messages = value.get("messages")
        if not messages:
            print("Evento sin messages (status update).")
            return "ok", 200

        message = messages[0]

        # Deduplicación
        message_id = message.get("id")
        if message_id:
            if message_id in PROCESSED_MESSAGE_IDS_SET:
                print(f"Mensaje duplicado {message_id}, ignorado.")
                return "ok", 200

            PROCESSED_MESSAGE_IDS_SET.add(message_id)
            PROCESSED_MESSAGE_IDS.append(message_id)
            if len(PROCESSED_MESSAGE_IDS) > MAX_DEDUP:
                old = PROCESSED_MESSAGE_IDS.pop(0)
                PROCESSED_MESSAGE_IDS_SET.discard(old)

        from_number = message["from"]
        message_type = message.get("type")

        text_body = ""

        if message_type == "text":
            text_body = message.get("text", {}).get("body", "").strip()

        elif message_type == "button":
            text_body = message.get("button", {}).get("text", "").strip()

        elif message_type == "interactive":
            inter = message.get("interactive", {})
            itype = inter.get("type")

            if itype == "button_reply":
                text_body = inter.get("button_reply", {}).get("title", "").strip()
            elif itype == "list_reply":
                text_body = inter.get("list_reply", {}).get("title", "").strip()

        else:
            print(f"Mensaje tipo '{message_type}' no soportado.")
            return "ok", 200

        if not text_body:
            print("Mensaje vacío.")
            return "ok", 200

        print(f"Mensaje desde {from_number}: {text_body}")

    except Exception as e:
        print("Error parseando estructura WhatsApp:", repr(e))
        return "ok", 200

    # 3) Reset memoria
    if text_body.lower() in ["reset", "reiniciar", "borrar memoria", "resetear memoria"]:
        reset_user_history(from_number)
        send_whatsapp_message(
            from_number,
            "Listo. Reseteé la memoria del chat. Partimos de cero."
        )
        return "ok", 200

    # 4) Historial
    try:
        user_history = get_user_history(from_number)
    except Exception as e:
        print("ERROR get_user_history:", repr(e))
        user_history = []

    # 5) Prompt sistema
    system_message = {
        "role": "system",
        "content": (
            "Eres 'Cerebro de Patio', un supervisor experto en patios de centros de "
            "distribución y crossdock e-commerce en Chile. "
            "Respondes directo, operativo y accionable. "
            "Hablas con Christian, subgerente de operaciones."
        ),
    }

    messages_for_openai = (
        [system_message] + user_history + [{"role": "user", "content": text_body}]
    )

    # 6) Guardar mensaje usuario
    try:
        append_message(from_number, "user", text_body)
    except Exception as e:
        print("ERROR guardando mensaje user:", repr(e))

    # 7) OpenAI (tu función REST o SDK)
    try:
        reply = call_openai_chat(messages_for_openai)
        append_message(from_number, "assistant", reply)
    except Exception as e:
        print("ERROR OpenAI:", repr(e))
        reply = "Tuve un problema procesando el mensaje. Intenta nuevamente."

    # 8) Responder WhatsApp
    send_whatsapp_message(from_number, reply)
    return "ok", 200


# =========================================================
# MAIN (solo local)
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
