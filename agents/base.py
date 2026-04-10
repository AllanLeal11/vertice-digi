import os
import threading
from openai import OpenAI
from .marketing import MARKETING_PROMPT
from .ventas import VENTAS_PROMPT
from .desarrollador import DESARROLLADOR_PROMPT
from .soporte import SOPORTE_PROMPT
from .asistente import ASISTENTE_PROMPT
from .disenador import DISENADOR_PROMPT
from .router import detectar_agente, detectar_combinacion

# ==================== CONFIGURACIÓN OPENROUTER ====================
client = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# Modelo gratuito recomendado (muy potente y con buenos límites)
MODEL = "deepseek/deepseek-r1"   

MAX_TOKENS = 4000

AGENTES = {
    "marketing":     {"prompt": MARKETING_PROMPT,     "nombre": "Director de Marketing"},
    "ventas":        {"prompt": VENTAS_PROMPT,         "nombre": "Director Comercial"},
    "desarrollador": {"prompt": DESARROLLADOR_PROMPT,  "nombre": "Lead Developer"},
    "soporte":       {"prompt": SOPORTE_PROMPT,        "nombre": "Jefe de Soporte"},
    "asistente":     {"prompt": ASISTENTE_PROMPT,      "nombre": "Asistente Ejecutivo"},
    "disenador":     {"prompt": DISENADOR_PROMPT,      "nombre": "Diseñador Gráfico"},
}

def _llamar_openrouter(system_prompt: str, mensajes: list) -> str:
    """Llama a OpenRouter"""
    try:
        messages = [{"role": "system", "content": system_prompt}] + mensajes
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return f"[Error al conectar con OpenRouter: {str(e)}]"


def responder(mensaje: str, historial: list = None, agente_forzado: str = "auto") -> dict:
    if historial is None:
        historial = []

    # Detectar combinación paralela
    if agente_forzado in ("auto", "asistente"):
        combinacion = detectar_combinacion(mensaje)
        if combinacion:
            return responder_paralelo(mensaje, combinacion)

    # Agente único
    if agente_forzado and agente_forzado != "auto" and agente_forzado in AGENTES:
        agente_key = agente_forzado
    else:
        agente_key = detectar_agente(mensaje)

    agente = AGENTES[agente_key]
    mensajes = historial + [{"role": "user", "content": mensaje}]
    texto = _llamar_openrouter(agente["prompt"], mensajes)

    return {
        "agente": agente_key,
        "nombre_agente": agente["nombre"],
        "respuesta": texto,
        "modo": "normal",
    }


def responder_paralelo(mensaje: str, combinacion: dict) -> dict:
    """Múltiples agentes trabajan simultáneamente"""
    resultados = {}

    def trabajo_agente(agente_key: str):
        agente = AGENTES[agente_key]
        contexto = (
            f"Estás trabajando en equipo con otros agentes de Vértice Digital en esta tarea: {mensaje}\n\n"
            f"Equipo activo: {combinacion['descripcion']}\n\n"
            f"Vos sos el {agente['nombre']}. Ejecutá tu parte completa."
        )
        texto = _llamar_openrouter(agente["prompt"], [{"role": "user", "content": contexto}])
        resultados[agente_key] = {"respuesta": texto, "nombre": agente["nombre"]}

    threads = []
    for agente_key in combinacion["agentes"]:
        t = threading.Thread(target=trabajo_agente, args=(agente_key,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return {
        "modo": "paralelo",
        "combinacion": combinacion["nombre"],
        "descripcion": combinacion["descripcion"],
        "resultados": resultados,
        "agente": combinacion["agentes"][0],
        "nombre_agente": combinacion["descripcion"],
        "respuesta": resultados.get(combinacion["agentes"][0], {}).get("respuesta", ""),
    }
