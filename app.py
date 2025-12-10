# app.py
# Cerebro de Patio – Flask + OpenAI + WhatsApp Cloud API (Meta)

import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

# =========================================================
# CARGA VARIABLES DE ENTORNO
# =========================================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "cerebro_token_123")

if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY en el .env")
if not WHATSAPP_TOKEN:
    raise RuntimeError("Falta WHATSAPP_TOKEN en el .env")
if not WHATSAPP_PHONE_ID:
    raise RuntimeError("Falta WHATSAPP_PHONE_ID en el .env")

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

# =========================================================
# WEBHOOK – VERIFICACIÓN (GET)
# =========================================================
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print("=== VERIFICACIÓN WEBHOOK ===")
    print("mode:", mode)
    print("token:", token)
    print("challenge:", challenge)

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return challenge, 200

    return "Token de verificación inválido", 403


# =========================================================
# WEBHOOK – MENSAJES (POST)
# =========================================================
@app.route("/webhook", methods=["POST"])
def receive_message():
    # LOG BRUTO PARA DEBUG
    print("\n\n======================")
    print(">>> LLEGÓ UN POST A /webhook")
    print("Headers:", dict(request.headers))
    print("Raw body:", request.data)
    print("======================\n")

    # Intentar parsear JSON
    try:
        data = request.get_json()
        print("=== JSON PARSEADO ===")
        print(data)
    except Exception as e:
        print("ERROR parseando JSON:", e)
        return "ok", 200

    # Si no hay JSON, salimos
    if not data:
        print("No vino JSON en el body")
        return "ok", 200

    # 1) Extraer mensaje y número
    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        messages = value.get("messages")
        if not messages:
            print("No hay 'messages' en el payload (probablemente es un status).")
            return "ok", 200

        message = messages[0]
        from_number = message["from"]          # Número del usuario
        text_body = message["text"]["body"]    # Texto que escribió

        print(f"Mensaje desde {from_number}: {text_body}")

    except Exception as e:
        print("Error parseando estructura de WhatsApp:", e)
        return "ok", 200

    # 2) Llamar a OpenAI
    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres 'Cerebro de Patio', un supervisor experto de patio "
                        "en centros de distribución y crossdock de e-commerce en Chile. "
                        "Respondes directo, sin rodeos, con foco operativo."
                    ),
                },
                {"role": "user", "content": text_body},
            ],
        )
        reply = completion.choices[0].message.content
        print("Respuesta de OpenAI:", reply)

    except Exception as e:
        print("Error llamando a OpenAI:", e)
        reply = "Christian, tuve un problema hablando con el modelo. Intenta de nuevo en un momento."

    # 3) Enviar respuesta a WhatsApp
    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": from_number,
        "type": "text",
        "text": {"body": reply},
    }

    print("=== REQUEST HACIA WHATSAPP ===")
    print("URL:", url)
    print("Payload:", payload)

    resp = requests.post(url, headers=headers, json=payload)

    print("=== RESPUESTA DE WHATSAPP ===")
    print("Status:", resp.status_code)
    print("Body:", resp.text)

    return "ok", 200



# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
