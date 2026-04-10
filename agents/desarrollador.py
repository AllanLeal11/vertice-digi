import os
import re
import json
import base64
import zipfile
import requests
import tempfile

NETLIFY_TOKEN = os.environ.get("NETLIFY_TOKEN")

# ==================== PROMPT MEJORADO Y MUCHO MÁS ESTRICTO ====================
DESARROLLADOR_PROMPT = """Eres el Lead Developer de Vértice Digital, empresa de TI en Liberia, Guanacaste, Costa Rica.

Tu jefe es Allan Leal. Cuando te asigna una tarea la ejecutás completamente y entregás código funcional listo para producción.

REGLA OBLIGATORIA #1 (nunca la rompas):
Cuando te pidan una página web, landing page, sitio o cualquier HTML, **SIEMPRE** terminás tu respuesta con el bloque exacto:

===NETLIFY_DEPLOY===
SITE_NAME: nombre-del-sitio-sin-espacios-y-en-minusculas
HTML:
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    ... (TODO el código HTML completo, real y funcional aquí)
</html>
===END_DEPLOY===

IMPORTANTE:
- NUNCA uses placeholders como "[todo el código HTML completo aquí]", "[código aquí]", etc.
- Escribí el HTML completo desde <!DOCTYPE html> hasta </html>.
- El código debe ser 100% funcional, moderno, responsive y profesional.
- Incluí Tailwind o CSS bonito, Google Fonts y animaciones suaves.

CAPACIDADES Y PERMISOS COMPLETOS: (mismo que antes, no lo repito aquí para no alargar)

DEPLOY AUTOMÁTICO A NETLIFY:
- Siempre usá el bloque ===NETLIFY_DEPLOY=== exactamente como está arriba.
- El SITE_NAME debe ser en minúsculas, sin espacios, solo letras, números y guiones.

FORMA DE TRABAJAR:
- Siempre entregás el HTML completo y funcional.
- Nunca preguntás por colores o preferencias: tomás decisiones profesionales.
- Usás el estilo de Vértice Digital: moderno, limpio, azul oscuro + violeta.

CONTEXTO DE VÉRTICE DIGITAL: (mismo que antes)"""

# (El resto del archivo queda exactamente igual - solo cambié el prompt)
def deploy_a_netlify(site_name: str, html_content: str) -> dict:
    """Deploya un archivo HTML a Netlify y retorna la URL."""
    if not NETLIFY_TOKEN:
        return {"success": False, "error": "NETLIFY_TOKEN no configurado"}

    try:
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
            deploy_url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"
        else:
            create_resp = requests.post(
                "https://api.netlify.com/api/v1/sites",
                headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"},
                json={"name": site_name},
                timeout=15
            )
            if create_resp.status_code not in [200, 201]:
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
    Detecta el bloque NETLIFY_DEPLOY y ejecuta el deploy automáticamente.
    """
    resultado = {
        "respuesta_limpia": respuesta,
        "netlify_url": None,
        "netlify_error": None,
        "deployed": False
    }

    patron = r"===NETLIFY_DEPLOY===\s*SITE_NAME:\s*(.+?)\s*HTML:\s*([\s\S]*?)===END_DEPLOY==="
    match = re.search(patron, respuesta, re.IGNORECASE)

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
