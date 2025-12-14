# app.py
# Cerebro de Patio – Flask + WhatsApp Cloud API (Meta) + OpenAI (REST) + Postgres (Neon)
# - NO hace create_all al importar (evita cuelgues en Railway)
# - OpenAI via REST (evita errores httpx/proxies)
# - Webhook GET/POST rápido + logs claros
# - Memoria persistente por usuario en Postgres/SQLite

import os
import time
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, request
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError

# =========================================================
# ENV
# =========================================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "cerebro_token_123")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cerebro.db")

if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en variables de entorno")
if not WHATSAPP_TOKEN:
    raise RuntimeError("Falta WHATSAPP_TOKEN en variables de entorno")
if not WHATSAPP_PHONE_ID:
    raise RuntimeError("Falta WHATSAPP_PHONE_ID en variables de entorno")

# Log BD
if DATABASE_URL.startswith("sqlite:///"):
    db_file = DATABASE_URL.replace("sqlite:///", "", 1)
    db_abs_path = Path(db_file).resolve()
    print(">>> BD: SQLite")
    print(f">>> Archivo: {db_abs_path}")
else:
    print(">>> BD (DATABASE_URL):")
    print(f">>> {DATABASE_URL}")

# =========================================================
# Flask
# =========================================================
app = Flask(__name__)

# =========================================================
# DB (lazy init)
# =========================================================
Base = declarative_base()
SessionLocal = None
_engine = None
_db_ready = False

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

def init_db():
    """Inicializa engine/session/tables UNA VEZ, con timeout para no colgar Railway."""
    global SessionLocal, _engine, _db_ready

    if _db_ready:
        return True

    try:
        connect_args = {}
        if DATABASE_URL.startswith("postgresql"):
            # evita cuelgues en boot si Neon/pooler está lento
            connect_args = {"connect_timeout": 5}

        _engine = create_engine(
            DATABASE_URL,
            echo=False,
            future=True,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_timeout=10,
            connect_args=connect_args,
        )
        SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)

        # crear tablas, pero controlado (y rápido)
        Base.metadata.create_all(bind=_engine)

        _db_ready = True
        print(">>> DB init OK")
        return True

    except Exception as e:
        print(">>> DB init FAIL:", repr(e))
        _db_ready = False
        return False

def get_db_session():
    if not init_db():
        return None
    return SessionLocal()

# =========================================================
# Memoria
# =========================================================
MAX_HISTORY_MESSAGES = 20
PROCESSED_MESSAGE_IDS = set()

def get_or_create_user_by_phone(db, phone: str) -> User:
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def get_user_history(phone: str):
    db = get_db_session()
    if db is None:
        return []
    try:
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
        return history[-MAX_HISTORY_MESSAGES:]
    finally:
        db.close()

def append_message(phone: str, role: str, content: str):
    db = get_db_session()
    if db is None:
        return
    try:
        user = get_or_create_user_by_phone(db, phone)
        db.add(Message(user_id=user.id, role=role, content=content))
        db.commit()
    finally:
        db.close()

def reset_user_history(phone: str):
    db = get_db_session()
    if db is None:
        return
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            return
        db.query(Message).filter(Message.user_id == user.id).delete()
        db.commit()
    finally:
        db.close()

# =========================================================
# WhatsApp send
# =========================================================
def send_whatsapp_message(to_number: str, text: str):
    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": text}}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        print("WA send status:", resp.status_code, "body:", resp.text[:300])
    except Exception as e:
        print("WA send ERROR:", repr(e))

# =========================================================
# OpenAI REST
# =========================================================
def call_openai_chat(messages, model="gpt-4.1-mini"):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.2}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

# =========================================================
# Routes
# =========================================================
@app.route("/", methods=["GET"])
def healthcheck():
    return "OK - Cerebro de Patio running", 200

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print("=== VERIFY ===", mode, token, challenge)

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN and challenge:
        return challenge, 200

    return "Token de verificación inválido", 403

@app.route("/webhook", methods=["POST"])
def receive_message():
    print("\n=== POST /webhook ===")
    try:
        data = request.get_json(silent=True)
    except Exception as e:
        print("JSON parse ERROR:", repr(e))
        return "ok", 200

    if not data:
        print("No JSON body")
        return "ok", 200

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        messages = value.get("messages")
        if not messages:
            print("No messages (status event)")
            return "ok", 200

        message = messages[0]
        message_id = message.get("id")
        if message_id and message_id in PROCESSED_MESSAGE_IDS:
            print("Dup message ignored:", message_id)
            return "ok", 200
        if message_id:
            PROCESSED_MESSAGE_IDS.add(message_id)

        if message.get("type") != "text":
            print("Non-text ignored:", message.get("type"))
            return "ok", 200

        from_number = message["from"]
        text_body = (message.get("text", {}).get("body") or "").strip()

        print("From:", from_number, "Text:", text_body)

    except Exception as e:
        print("WhatsApp payload parse ERROR:", repr(e))
        return "ok", 200

    if not text_body:
        return "ok", 200

    # reset
    if text_body.lower() in ["reset", "reinicia", "reiniciar", "borrar memoria", "resetear memoria"]:
        reset_user_history(from_number)
        send_whatsapp_message(from_number, "Listo. Reseteé la memoria para este chat. Partimos de cero.")
        return "ok", 200

    # build prompt
    system_message = {
        "role": "system",
        "content": (
            "Eres 'Cerebro de Patio', un supervisor experto de patio en centros de distribución "
            "y crossdock de e-commerce en Chile. Respondes directo, accionable, con foco operativo. "
            "Si falta información, pide datos concretos."
        ),
    }

    history = get_user_history(from_number)
    messages_for_openai = [system_message] + history + [{"role": "user", "content": text_body}]

    # persist user msg
    append_message(from_number, "user", text_body)

    # call model
    try:
        reply = call_openai_chat(messages_for_openai)
        append_message(from_number, "assistant", reply)
    except Exception as e:
        print("OpenAI ERROR:", repr(e))
        reply = "Tuve un problema hablando con el modelo. Intenta de nuevo en un momento."

    send_whatsapp_message(from_number, reply)
    return "ok", 200

# Local run only
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
