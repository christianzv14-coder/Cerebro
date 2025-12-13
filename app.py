# app.py
# Cerebro de Patio – Flask + OpenAI + WhatsApp Cloud API (Meta)
# - Memoria persistente en base de datos (SQLite / Postgres)
# - Memoria por usuario basada en tablas users + messages
# - Filtro de tipo de mensaje y deduplicación de mensajes
# - Listo para local y nube (Render/Railway/etc.)

import os
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, request
from dotenv import load_dotenv
from openai import OpenAI

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

# =========================================================
# BASE DE DATOS
# =========================================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cerebro.db")

if DATABASE_URL.startswith("sqlite:///"):
    db_file = DATABASE_URL.replace("sqlite:///", "", 1)
    db_abs_path = Path(db_file).resolve()
    print(">>> BASE DE DATOS USADA: SQLite")
    print(f">>> ARCHIVO BD: {db_abs_path}")
else:
    print(">>> BASE DE DATOS USADA por DATABASE_URL:")
    print(f">>> {DATABASE_URL}")

# =========================================================
# CLIENTES
# =========================================================
client = OpenAI(api_key=OPENAI_API_KEY)
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

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    phone = Column(String(32), unique=True, index=True)
    name = Column(String(255), nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(16))  # 'user' / 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="messages")


Base.metadata.create_all(bind=engine)

MAX_HISTORY_MESSAGES = 20
PROCESSED_MESSAGE_IDS = set()

# =========================================================
# OWNER / SEGURIDAD DURA
# =========================================================
OWNER_PHONE = (os.getenv("OWNER_PHONE") or "").strip()


def normalize_phone(p: str) -> str:
    return p.replace("+", "").replace(" ", "").strip()


def is_owner(phone: str) -> bool:
    return OWNER_PHONE != "" and normalize_phone(phone) == normalize_phone(OWNER_PHONE)


# =========================================================
# FUNCIONES BD
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
        print("WhatsApp status:", resp.status_code, resp.text)
    except Exception as e:
        print("Error enviando mensaje a WhatsApp:", e)


# =========================================================
# HEALTHCHECK
# =========================================================
@app.route("/", methods=["GET"])
def healthcheck():
    return "Cerebro de Patio está corriendo con memoria en BD.", 200


# =========================================================
# WEBHOOK VERIFICACIÓN
# =========================================================
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return challenge, 200

    return "Token de verificación inválido", 403


# =========================================================
# WEBHOOK MENSAJES
# =========================================================
@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    if not data:
        return "ok", 200

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        messages = value.get("messages")
        if not messages:
            return "ok", 200

        message = messages[0]

        message_id = message.get("id")
        if message_id and message_id in PROCESSED_MESSAGE_IDS:
            return "ok", 200
        if message_id:
            PROCESSED_MESSAGE_IDS.add(message_id)

        if message.get("type") != "text":
            return "ok", 200

        from_number = message["from"]
        text_body = message["text"]["body"].strip()

    except Exception:
        return "ok", 200

    lower_text = text_body.lower()
    if lower_text in [
        "reset",
        "reinicia",
        "reiniciar",
        "borrar memoria",
        "resetear memoria",
    ]:
        reset_user_history(from_number)
        send_whatsapp_message(
            from_number,
            "Listo. Reseteé la memoria para este chat. Partimos de cero.",
        )
        return "ok", 200

    try:
        user_history = get_user_history(from_number)
    except Exception:
        user_history = []

    system_message = {
        "role": "system",
        "content": (
            "Eres 'Cerebro de Patio', un supervisor experto de patio en centros de "
            "distribución y crossdock de e-commerce en Chile. "
            "Respondes directo, sin rodeos, con foco operativo. "
            "Tus respuestas deben ser accionables."
        ),
    }

    messages_for_openai = (
        [system_message]
        + user_history
        + [{"role": "user", "content": text_body}]
    )

    append_message(from_number, "user", text_body)

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages_for_openai,
        )
        reply = completion.choices[0].message.content
        append_message(from_number, "assistant", reply)
    except Exception:
        reply = "Tuve un problema hablando con el modelo. Intenta de nuevo."

    send_whatsapp_message(from_number, reply)
    return "ok", 200


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
