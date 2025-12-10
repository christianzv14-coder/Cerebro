# app.py
# Cerebro de Patio – Backend Flask + OpenAI + Twilio (WhatsApp)

import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI, RateLimitError

# =========================================================
# CONFIGURACIÓN OPENAI
# =========================================================

# Opción simple para pruebas: pegar tu API key aquí
OPENAI_API_KEY = "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"

# Si prefieres variable de entorno:
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# =========================================================
# CEREBRO DEL SUPERVISOR DE PATIO (SYSTEM PROMPT)
# =========================================================

SYSTEM_PROMPT = """
Eres el 'Cerebro de Patio', un supervisor experto de patio y coordinador de flota
en centros de distribución y crossdock de e-commerce y retail en Chile.

Tu forma de trabajar:
- Respondes directo, sin relleno, con foco operativo.
- Siempre propones acciones concretas (qué hacer ahora, qué medir, a quién llamar).
- Piensas como jefe de turno que cuida SLA, seguridad, orden y costos.

Contexto de tu rol:
- Gestionas llegada y salida de flotas: última milla, primera milla, troncales y cargas regionales.
- Aseguras uso eficiente de cortinas/andenes y orden del patio.
- Reaccionas ante atrasos, ausencias, quiebres de flota y problemas de documentación.
- Te preocupan KPIs como: cumplimiento de ETA/ETD, % ocupación de cortinas, puntualidad de salidas,
  uso de backup, y tiempos muertos de camiones y personas.

Estilo de respuesta:
- Explica siempre en pasos: 1), 2), 3)…
- Si falta información, parte aclarando qué asumirás.
- Puedes pedir más datos, pero igual propones un plan base con lo que tienes.
- Da opciones tipo plan A / plan B cuando haga sentido.

Nunca respondas como modelo genérico de chat. Siempre responde como
un supervisor senior hablando con otro supervisor/jefe que está en el patio.
"""

# =========================================================
# APP FLASK
# =========================================================

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health():
    """Endpoint simple para verificar que el servidor está vivo."""
    return {"status": "online", "service": "cerebro-patio"}


@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    """
    Endpoint que Twilio llama cuando llega un mensaje de WhatsApp.
    Espera un parámetro 'Body' con el texto del usuario.
    Devuelve una respuesta en formato TwiML.
    """
    user_message = request.values.get("Body", "").strip()

    # Si no vino mensaje
    if not user_message:
        resp = MessagingResponse()
        resp.message("No recibí mensaje. Intenta de nuevo enviando texto.")
        return str(resp)

    # Llamada al modelo de OpenAI con manejo de errores
    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",  # puedes cambiar a gpt-4.1, gpt-4o-mini, etc.
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
        )

        reply_text = completion.choices[0].message.content

    except RateLimitError:
        # Sin saldo / límite de uso alcanzado
        reply_text = (
            "No puedo responder ahora porque la cuenta de API no tiene saldo o llegó al "
            "límite de uso. Pide al administrador revisar el billing de OpenAI."
        )
    except Exception as e:
        # Error genérico inesperado
        reply_text = (
            "Tuve un error técnico procesando la consulta del patio. "
            "Revisa el servidor o vuelve a intentar en unos minutos.\n\n"
            f"(Detalle técnico: {type(e).__name__})"
        )

    # Construir respuesta para WhatsApp (Twilio)
    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)


# =========================================================
# MAIN – Solo para correr localmente
# =========================================================

if __name__ == "__main__":
    # debug=True solo en desarrollo; en producción debe ir en False
    app.run(host="0.0.0.0", port=5000, debug=True)
