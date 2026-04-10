import os
from openai import OpenAI
from .marketing import MARKETING_PROMPT
from .ventas import VENTAS_PROMPT
from .desarrollador import DESARROLLADOR_PROMPT
from .soporte import SOPORTE_PROMPT
from .asistente import ASISTENTE_PROMPT
from .disenador import DISENADOR_PROMPT

# Usamos el mismo cliente de OpenRouter
client = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

ROUTER_PROMPT = """Eres el router de Vértice Digital. Analizás el mensaje y respondés con UNA SOLA PALABRA:

- "marketing" → redes sociales, publicidad, SEO, contenido, posts, campañas
- "ventas" → precios, cotizaciones, propuestas, contratos, clientes nuevos
- "desarrollador" → código, web, app, página, sitio, programar, sistema, bot, deploy
- "soporte" → errores, problemas, bugs, caído, lento, arreglar
- "disenador" → diseño, logo, colores, tipografía, identidad visual
- "asistente" → agenda, email, tareas, organización, recordatorio, resumen

Respondé SOLO con una de esas palabras."""

COMBINACIONES_PARALELO = [
    {"nombre": "web_completa", "palabras": ['web', 'página', 'pagina', 'sitio', 'landing', 'frontend', 'interfaz'], "agentes": ["desarrollador", "disenador", "ventas"], "descripcion": "Desarrollador + Diseñador + Ventas"},
    {"nombre": "app", "palabras": ['app', 'aplicación', 'aplicacion', 'sistema', 'plataforma', 'dashboard'], "agentes": ["desarrollador", "disenador", "ventas"], "descripcion": "Desarrollador + Diseñador + Ventas"},
    {"nombre": "automatizacion", "palabras": ['bot', 'automatizar', 'automatización', 'automatizacion', 'webhook', 'integración', 'integracion', 'script'], "agentes": ["desarrollador", "ventas"], "descripcion": "Desarrollador + Ventas"},
    {"nombre": "campana", "palabras": ['campaña', 'campana', 'lanzamiento', 'promoción', 'promocion', 'anuncio', 'publicidad'], "agentes": ["marketing", "disenador", "ventas"], "descripcion": "Marketing + Diseñador + Ventas"},
    {"nombre": "contenido_redes", "palabras": ['post', 'publicación', 'publicacion', 'contenido', 'redes', 'instagram', 'facebook', 'tiktok'], "agentes": ["marketing", "disenador"], "descripcion": "Marketing + Diseñador"},
    {"nombre": "soporte_cliente", "palabras": ['error', 'caído', 'caido', 'falla', 'problema', 'bug', 'roto', 'no funciona'], "agentes": ["soporte", "asistente"], "descripcion": "Soporte + Asistente"},
    {"nombre": "propuesta_cliente", "palabras": ['propuesta', 'cotización', 'cotizacion', 'presupuesto', 'cliente nuevo', 'prospecto'], "agentes": ["ventas", "asistente"], "descripcion": "Ventas + Asistente"},
    {"nombre": "identidad_marca", "palabras": ['logo', 'marca', 'identidad', 'branding', 'colores', 'tipografía', 'tipografia'], "agentes": ["disenador", "marketing"], "descripcion": "Diseñador + Marketing"},
]

def detectar_agente(mensaje: str) -> str:
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1",
            max_tokens=10,
            messages=[
                {"role": "system", "content": ROUTER_PROMPT},
                {"role": "user", "content": mensaje}
            ]
        )
        agente = response.choices[0].message.content.strip().lower()
        agentes_validos = ["marketing", "ventas", "desarrollador", "soporte", "disenador", "asistente"]
        return agente if agente in agentes_validos else "asistente"
    except Exception:
        return "asistente"

def detectar_combinacion(mensaje: str) -> dict | None:
    """Detecta si el mensaje activa una combinación paralela de agentes."""
    msg = mensaje.lower()
    for combo in COMBINACIONES_PARALELO:
        if any(palabra in msg for palabra in combo["palabras"]):
            return combo
    return None
