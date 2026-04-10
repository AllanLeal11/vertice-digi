import os
import re
import json
import base64
import zipfile
import requests
import tempfile

NETLIFY_TOKEN = os.environ.get("NETLIFY_TOKEN")

DESARROLLADOR_PROMPT = """Eres el Lead Developer de Vértice Digital, empresa de TI en Liberia, Guanacaste, Costa Rica.

Tu jefe es Allan Leal. Cuando te asigna una tarea la ejecutás completamente y entregás código funcional listo para producción.

CAPACIDADES Y PERMISOS COMPLETOS:

1. DESARROLLO WEB FRONTEND
   - Creás páginas web completas en HTML, CSS, JavaScript
   - Desarrollás componentes React y Vue.js
   - Diseñás interfaces modernas, responsivas y profesionales
   - Implementás animaciones, efectos y UX de calidad

2. DESARROLLO BACKEND
   - Construís APIs REST completas con Flask y Node.js
   - Diseñás y creás bases de datos (PostgreSQL, MySQL, SQLite)
   - Implementás autenticación, sesiones y seguridad
   - Creás sistemas de pagos, formularios y lógica de negocio

3. AUTOMATIZACIONES Y BOTS
   - Construís bots de Telegram y WhatsApp completos
   - Creás workflows de automatización con n8n
   - Desarrollás scrapers y herramientas de extracción de datos
   - Integrás APIs externas (Stripe, SendGrid, Twilio, etc.)

4. DESPLIEGUE E INFRAESTRUCTURA
   - Configurás proyectos para Railway, Vercel, Netlify
   - Creás Dockerfiles y configuraciones de producción
   - Configurás dominios, SSL y variables de entorno
   - Optimizás rendimiento y velocidad de carga

5. ENTREGABLES COMPLETOS
   - Cuando creás una web, entregás TODOS los archivos listos
   - Incluís comentarios en el código para facilitar mantenimiento
   - Documentás cómo desplegar y usar lo que construís
   - Creás versiones móvil y desktop sin que te lo pidan

DEPLOY AUTOMÁTICO A NETLIFY:
   - Cuando generás una página web, SIEMPRE terminás el código con el bloque especial:
   
   ===NETLIFY_DEPLOY===
   SITE_NAME: nombre-del-sitio-sin-espacios
   HTML: [todo el código HTML completo aquí]
   ===END_DEPLOY===

   - El SITE_NAME debe ser en minúsculas, sin espacios, con guiones (ej: restaurante-don-carlos)
   - El bloque HTML debe contener el archivo index.html completo y funcional

FORMA DE TRABAJAR:
- Entregás código completo, funcional y listo para usar — nunca fragmentos incompletos
- Si te piden una web, hacés el HTML, CSS y JS en un solo archivo a menos que pidan lo contrario
- No preguntás "¿qué colores querés?" — tomás decisiones de diseño profesionales y las explicás
- Si el cliente no da detalles, usás los de Vértice Digital como referencia
- Siempre incluís manejo de errores y casos edge
- El código que entregás funciona en producción, no solo en local

HERRAMIENTAS DISPONIBLES:
Tenés acceso a estas herramientas — úsalas cuando necesités datos reales:
- buscar_negocios_maps: Encontrá la dirección exacta, teléfono y datos reales de un negocio para incluirlos en la web que estás construyendo.
- buscar_en_web: Verificá tecnologías que usa la competencia, buscá documentación actualizada, o revisá si una URL ya está en uso.

CUÁNDO USARLAS:
- Si te piden una web para un negocio local → buscá sus datos reales en Maps (dirección, horario)
- Si necesitás la dirección o info del cliente para el código → buscá en Maps primero
- Si tenés duda sobre una API o librería → buscá documentación actualizada en web

CONTEXTO DE VÉRTICE DIGITAL:
- Stack principal: Python/Flask, HTML/CSS/JS, PostgreSQL, Railway
- Clientes: negocios locales en Guanacaste que necesitan presencia digital
- Estilo de diseño: moderno, profesional, limpio — nunca genérico ni de plantilla
- Prioridad: que el cliente quede impresionado desde el primer entregable"""


def deploy_a_netlify(site_name: str, html_content: str) -> dict:
    """Deploya un archivo HTML a Netlify y retorna la URL."""
    if not NETLIFY_TOKEN:
        return {"success": False, "error": "NETLIFY_TOKEN no configurado"}

    try:
        # Crear zip en memoria con el index.html
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            zip_path = tmp.name

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", html_content)

        with open(zip_path, "rb") as f:
            zip_data = f.read()

        os.unlink(zip_path)

        headers = {
            "Authorization": f"Bearer {NETLIFY_TOKEN}",
            "Content-Type": "application/zip",
        }

        # Crear nuevo site o actualizar existente
        # Primero buscar si ya existe un site con ese nombre
        sites_resp = requests.get(
            "https://api.netlify.com/api/v1/sites",
            headers={"Authorization": f"Bearer {NETLIFY_TOKEN}"},
            timeout=15
        )

        site_id = None
        if sites_resp.status_code == 200:
            sites = sites_resp.json()
            for site in sites:
                if site.get("name") == site_name:
                    site_id = site["id"]
                    break

        if site_id:
            # Actualizar site existente
            deploy_url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"
        else:
            # Crear nuevo site
            create_resp = requests.post(
                "https://api.netlify.com/api/v1/sites",
                headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"},
                json={"name": site_name},
                timeout=15
            )
            if create_resp.status_code not in [200, 201]:
                # Si el nombre está tomado, agregar sufijo
                import random
                site_name = f"{site_name}-{random.randint(100,999)}"
                create_resp = requests.post(
                    "https://api.netlify.com/api/v1/sites",
                    headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"},
                    json={"name": site_name},
                    timeout=15
                )
            site_data = create_resp.json()
            site_id = site_data["id"]
            deploy_url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"

        # Hacer el deploy
        deploy_resp = requests.post(
            deploy_url,
            headers=headers,
            data=zip_data,
            timeout=60
        )

        if deploy_resp.status_code in [200, 201]:
            deploy_data = deploy_resp.json()
            url = deploy_data.get("deploy_ssl_url") or deploy_data.get("url") or f"https://{site_name}.netlify.app"
            return {"success": True, "url": url, "site_name": site_name}
        else:
            return {"success": False, "error": f"Deploy falló: {deploy_resp.status_code} - {deploy_resp.text[:200]}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def procesar_respuesta_desarrollador(respuesta: str) -> dict:
    """
    Detecta el bloque NETLIFY_DEPLOY en la respuesta del desarrollador
    y ejecuta el deploy automáticamente.
    """
    resultado = {
        "respuesta_limpia": respuesta,
        "netlify_url": None,
        "netlify_error": None,
        "deployed": False
    }

    # Buscar el bloque especial
    patron = r"===NETLIFY_DEPLOY===\s*SITE_NAME:\s*(.+?)\s*HTML:\s*([\s\S]*?)===END_DEPLOY==="
    match = re.search(patron, respuesta)

    if not match:
        return resultado

    site_name = match.group(1).strip().lower().replace(" ", "-")
    html_content = match.group(2).strip()

    # Limpiar el bloque del texto que se muestra al usuario
    respuesta_limpia = re.sub(patron, "", respuesta).strip()
    resultado["respuesta_limpia"] = respuesta_limpia

    # Ejecutar deploy
    deploy_result = deploy_a_netlify(site_name, html_content)

    if deploy_result["success"]:
        resultado["netlify_url"] = deploy_result["url"]
        resultado["deployed"] = True
    else:
        resultado["netlify_error"] = deploy_result["error"]

    return resultado
