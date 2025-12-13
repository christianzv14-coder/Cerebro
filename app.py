# app.py
# Cerebro de Patio – Flask + OpenAI + WhatsApp Cloud API (Meta)
# - Memoria persistente en BD (SQLite / Postgres)
# - Memoria por usuario (users + messages)
# - Listo para Railway + Gunicorn

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
# VARIABLES DE ENTORNO
# =========================================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "cerebro_token_123")

if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY")
if not WHATSAPP_TOKEN:
    raise RuntimeError("Falta WHATSAPP_TOKEN")
if not WHATSAPP_PHONE_ID:
    raise RuntimeError("Falta WHATSAPP_PHONE_ID")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cerebro.db")

# Log BD
if DATABASE_URL.startswith("sqlite:///"):
    db_file = DATABASE_URL.replace("sqlite:///", "", 1)
    print(">>> BD SQLite:", Path(db_file).resolve())
else:
    print(">>> BD Postgres:", DATABASE_URL)

# =========================================================
# APP + OPENAI
# =========================================================
app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# =========================================================
# SQLALCHEMY
# =========================================================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    phone = Column(String(32), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(16))  # user / assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", backref="messages")


Base.metadata.create_all(bind=engine)

MAX_HISTORY = 20
PROCESSED_IDS = set()

# =========================================================
# HELPERS BD
# =========================================================
def get_session():
    return SessionLocal()


def get_or_create_user(db, phone):
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def save_message(phone, role, content):
    with get_session() as db:
        user = get_or_create_user(db, phone)
        db.add(Message(user_id=user.id, role=role, content=content))
        db.commit()


def get_history(phone):
    with get_session() as db:
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
        return history[-MAX_HISTORY:]


def reset_history(phone):
    with get_session() as db:
        user = db.query(User).filter(User.phone == phone).first()
        if user:
            db.query(Message).filter(Message.user_id == user.id).delete()
            db.commit()


# =========================================================
# WHATSAPP SEND
# =========================================================
def send_whatsapp(to, text):
    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    requests.post(url, headers=headers, json=payload)


# =========================================================
# ROUTES
# =========================================================
@app.route("/", methods=["GET"])
def health():
    return "Cerebro OK", 200


@app.route("/webhook", methods=["GET"])
def verify():
    if (
        request.args.get("hub.mode") == "subscribe"
        and request.args.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN
    ):
        return request.args.get("hub.challenge"), 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def receive():
    data = request.get_json()
    if not data:
        return "ok", 200

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
    except Exception:
        return "ok", 200

    msg_id = message.get("id")
    if msg_id and msg_id in PROCESSED_IDS:
        return "ok", 200
    if msg_id:
        PROCESSED_IDS.add(msg_id)

    if message.get("type") != "text":
        return "ok", 200

    phone = message["from"]
    text = message["text"]["body"].strip()

    if text.lower() in ["reset", "reiniciar", "borrar memoria"]:
        reset_history(phone)
        send_whatsapp(phone, "Memoria reseteada. Partimos de cero.")
        return "ok", 200

    history = get_history(phone)

    system = {
        "role": "system",
        "content": (
            "Eres Cerebro de Patio, supervisor experto de patios "
            "logísticos y crossdock en Chile. Respondes directo, "
            "operativo y accionable."
        ),
    }

    messages = [system] + history + [{"role": "user", "content": text}]

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
        )
        reply = completion.choices[0].message.content
    except Exception:
        reply = "Error interno. Intenta nuevamente."

    save_message(phone, "user", text)
    save_message(phone, "assistant", reply)

    send_whatsapp(phone, reply)
    return "ok", 200


# =========================================================
# LOCAL
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
