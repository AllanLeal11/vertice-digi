import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def enviar_mensaje(texto: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": texto,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except:
        return False

def enviar_aprobacion(tipo: str, contenido: str, id_aprobacion: str) -> bool:
    texto = (
        f"<b>📋 PENDIENTE DE APROBACIÓN</b>\n"
        f"<b>Tipo:</b> {tipo}\n"
        f"<b>ID:</b> {id_aprobacion}\n\n"
        f"{contenido}\n\n"
        f"Respondé en el chat:\n"
        f"✅ <code>aprobar {id_aprobacion}</code>\n"
        f"❌ <code>rechazar {id_aprobacion}</code>\n"
        f"✏️ <code>editar {id_aprobacion} [tu feedback]</code>"
    )
    return enviar_mensaje(texto)

def notificar(mensaje: str) -> bool:
    texto = f"<b>🔔 Vértice Digital</b>\n\n{mensaje}"
    return enviar_mensaje(texto)
