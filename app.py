# app.py
# Cerebro de Patio – Flask + OpenAI + WhatsApp Cloud API (Meta)
# - Memoria por usuario en RAM
# - Filtro de tipo de mensaje
# - Deduplicación de mensajes
# - Listo para correr en local y en la nube (Render/Railway/etc.)

import os
import requests
from flask import Flask, request
from dotenv import load_dotenv
from openai import OpenAI

# =========================================================
# CARGA DE VARIABLES DE ENTORNO
# =========================================================
# En local puedes usar un archivo .env
# En la nube, la plataforma inyecta las variables al entorno.
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

# Cliente OpenAI (SDK nuevo)
client = OpenAI(api_key=OPENAI_API_KEY)

# Instancia Flask
app = Flask(__name__)

# =========================================================
# MEMORIA EN RAM POR NÚMERO DE WHATSAPP
# =========================================================
# Diccionario: { "numero_whatsapp": [ {role: "...", content: "..."}, ... ] }
CONVERSATIONS = {}
MAX_HISTORY_MESSAGES = 20  # Aprox. 10 turnos (user+assistant)

# Set para evitar procesar el mismo mensaje varias veces
PROCESSED_MESSAGE_IDS = set()


def get_user_history(from_number: str):
    """Obtiene el historial del usuario desde memoria (RAM)."""
    return CONVERSATIONS.get(from_number, [])


def save_user_history(from_number: str, history):
    """Guarda (y recorta) el historial del usuario en memoria."""
    if len(history) > MAX_HISTORY_MESSAGES:
        history = history[-MAX_HISTORY_MESSAGES:]
    CONVERSATIONS[from_number] = history


def reset_user_history(from_number: str):
    """Elimina el historial del usuario en memoria."""
    if from_number in CONVERSATIONS:
        del CONVERSATIONS[from_number]


# =========================================================
# HEALTHCHECK / ROOT
# =========================================================
@app.route("/", methods=["GET"])
def healthcheck():
    """
    Endpoint simple para comprobar que el servicio está vivo.
    Útil para pruebas en la nube (Render/Railway/etc.).
    """
    return "Cerebro de Patio está corriendo.", 200


# =========================================================
# WEBHOOK – VERIFICACIÓN (GET)
# =========================================================
@app.route("/webhook", methods=["GET"])
def verify():
    """
    Endpoint que Meta (WhatsApp Cloud) usa una sola vez
    para verificar que el webhook es tuyo.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print("=== VERIFICACIÓN WEBHOOK ===")
    print("mode:", mode)
    print("token:", token)
    print("challenge:", challenge)

    # Meta envía mode=subscribe y el verify_token que tú configuraste
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        # Debes devolver el challenge tal cual, con status 200
        return challenge, 200

    return "Token de verificación inválido", 403


# =========================================================
# WEBHOOK – MENSAJES (POST)
# =========================================================
@app.route("/webhook", methods=["POST"])
def receive_message():
    """
    Endpoint que recibe los mensajes de WhatsApp.
    Aquí parseamos el JSON, filtramos, usamos OpenAI y respondemos.
    """
    print("\n\n======================")
    print(">>> LLEGÓ UN POST A /webhook")
    print("Headers:", dict(request.headers))
    print("Raw body:", request.data)
    print("======================\n")

    # 1) Intentar parsear JSON
    try:
        data = request.get_json()
        print("=== JSON PARSEADO ===")
        print(data)
    except Exception as e:
        print("ERROR parseando JSON:", e)
        return "ok", 200

    if not data:
        print("No vino JSON en el body")
        return "ok", 200

    # 2) Extraer mensaje y número (solo si viene 'messages')
    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        messages = value.get("messages")
        if not messages:
            print("No hay 'messages' en el payload (probablemente es un status).")
            return "ok", 200

        message = messages[0]

        # 2.1) Deduplicación por message_id
        message_id = message.get("id")
        if message_id:
            if message_id in PROCESSED_MESSAGE_IDS:
                print(f"Mensaje {message_id} ya procesado. Ignorando.")
                return "ok", 200
            PROCESSED_MESSAGE_IDS.add(message_id)

        # 2.2) Solo aceptamos mensajes de texto
        message_type = message.get("type")
        if message_type != "text":
            print(f"Mensaje ignorado: tipo '{message_type}' no soportado.")
            return "ok", 200

        from_number = message["from"]  # Número del usuario (incluye código país)
        text_body = message.get("text", {}).get("body", "").strip()

        print(f"Mensaje desde {from_number}: {text_body}")

    except Exception as e:
        print("Error parseando estructura de WhatsApp:", e)
        return "ok", 200

    # 3) Comando para resetear memoria por usuario
    lower_text = text_body.lower()
    if lower_text in ["reset", "reinicia", "reiniciar", "borrar memoria", "resetear memoria"]:
        reset_user_history(from_number)
        reply_reset = (
            "Listo Christian, reseteé la memoria para este chat. "
            "Partimos de cero en el patio."
        )
        send_whatsapp_message(from_number, reply_reset)
        return "ok", 200

    # 4) Construir contexto con memoria
    user_history = get_user_history(from_number)

    # Mensaje de sistema (rol del asistente)
    system_message = {
        "role": "system",
        "content": (
            "Eres 'Cerebro de Patio', un supervisor experto de patio en centros de "
            "distribución y crossdock de e-commerce en Chile. "
            "Respondes directo, sin rodeos, con foco operativo. "
            "Conoces conceptos como bloques de salida, andenes, flota tercerizada, "
            "conductores, rutas, SLAs, atrasos, mermas y seguridad en el patio. "
            "Hablas con Christian, subgerente de operaciones, y tus respuestas deben ser "
            "accionables en el piso: qué hacer, en qué orden y con quién."
        ),
    }

    # Historial + nuevo mensaje del usuario
    messages_for_openai = [system_message] + user_history + [
        {"role": "user", "content": text_body}
    ]

    # 5) Llamar a OpenAI
    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages_for_openai,
        )
        reply = completion.choices[0].message.content
        print("Respuesta de OpenAI:", reply)

        # Actualizar memoria: agregamos user y assistant
        user_history.append({"role": "user", "content": text_body})
        user_history.append({"role": "assistant", "content": reply})
        save_user_history(from_number, user_history)

    except Exception as e:
        print("Error llamando a OpenAI:", e)
        reply = (
            "Christian, tuve un problema hablando con el modelo. "
            "Intenta de nuevo en un momento o revisa el servidor."
        )

    # 6) Enviar respuesta a WhatsApp
    send_whatsapp_message(from_number, reply)

    return "ok", 200


# =========================================================
# FUNCIÓN AUXILIAR PARA ENVIAR MENSAJES A WHATSAPP
# =========================================================
def send_whatsapp_message(to_number: str, text: str):
    """Envía un mensaje de texto a WhatsApp usando la Cloud API."""
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

    print("=== REQUEST HACIA WHATSAPP ===")
    print("URL:", url)
    print("Payload:", payload)

    try:
        resp = requests.post(url, headers=headers, json=payload)
        print("=== RESPUESTA DE WHATSAPP ===")
        print("Status:", resp.status_code)
        print("Body:", resp.text)
    except Exception as e:
        print("Error enviando mensaje a WhatsApp:", e)


# =========================================================
# MAIN (solo para entorno local)
# En la nube se usará: gunicorn app:app
# =========================================================
if __name__ == "__main__":
    # En local puedes usar FLASK_DEBUG=true para ver más logs
    debug_mode = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
