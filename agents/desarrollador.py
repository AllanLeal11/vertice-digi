import os
import re
import zipfile
import requests
import tempfile

NETLIFY_TOKEN = os.environ.get("NETLIFY_TOKEN")

# ==================== PROMPT BLINDADO - ESTA VERSIÓN NO FALLA ====================
DESARROLLADOR_PROMPT = """Eres el Lead Developer de Vértice Digital.

REGLA ABSOLUTA E INQUEBRANTABLE:
Cuando te pidan una página web, landing page o HTML, **PROHIBIDO** usar Markdown (#, ##, -, **, listas con guiones, etc.).

Debes responder **ÚNICAMENTE** con este formato exacto y nada más:

✅ Listo Allan. Ya desplegué la web de Vértice Digital en Netlify.

===NETLIFY_DEPLOY===
SITE_NAME: vertice-digital
HTML:
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vértice Digital</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&amp;family=Inter:wght@400;500&amp;display=swap" rel="stylesheet">
</head>
<body class="bg-[#1a1a2e] text-white font-sans">
    <!-- AQUÍ VA TODO EL HTML REAL Y COMPLETO -->
</body>
</html>
===END_DEPLOY===

Nunca pongas Markdown. Nunca dejes el HTML incompleto. Nunca pongas texto después del bloque ===END_DEPLOY===.

Usa siempre Tailwind + Poppins + Inter. Hazlo moderno, profesional y mobile-first."""

def deploy_a_netlify(site_name: str, html_content: str) -> dict:
    if not NETLIFY_TOKEN:
        return {"success": False, "error": "NETLIFY_TOKEN no configurado"}

    try:
        html_content = html_content.strip()

        # FORZAR HTML VÁLIDO (esto arregla la mayoría de los casos)
        if not html_content.startswith("<!DOCTYPE html>"):
            html_content = "<!DOCTYPE html>\n" + html_content
        if "</html>" not in html_content.lower():
            html_content += "\n</html>"

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            zip_path = tmp.name

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", html_content)

        with open(zip_path, "rb") as f:
            zip_data = f.read()

        os.unlink(zip_path)

        headers = {"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/zip"}

        # Crear o actualizar site
        sites_resp = requests.get("https://api.netlify.com/api/v1/sites", headers={"Authorization": f"Bearer {NETLIFY_TOKEN}"}, timeout=15)
        site_id = None
        if sites_resp.status_code == 200:
            for site in sites_resp.json():
                if site.get("name") == site_name:
                    site_id = site["id"]
                    break

        if site_id:
            deploy_url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"
        else:
            create_resp = requests.post(
                "https://api.netlify.com/api/v1/sites",
                headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"},
                json={"name": site_name}, timeout=15
            )
            if create_resp.status_code not in [200, 201]:
                import random
                site_name = f"{site_name}-{random.randint(100,999)}"
                create_resp = requests.post("https://api.netlify.com/api/v1/sites", headers={"Authorization": f"Bearer {NETLIFY_TOKEN}", "Content-Type": "application/json"}, json={"name": site_name}, timeout=15)
            site_id = create_resp.json()["id"]
            deploy_url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"

        deploy_resp = requests.post(deploy_url, headers=headers, data=zip_data, timeout=60)

        if deploy_resp.status_code in [200, 201]:
            deploy_data = deploy_resp.json()
            url = deploy_data.get("deploy_ssl_url") or deploy_data.get("url") or f"https://{site_name}.netlify.app"
            return {"success": True, "url": url, "site_name": site_name}
        else:
            return {"success": False, "error": f"Deploy falló: {deploy_resp.status_code}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def procesar_respuesta_desarrollador(respuesta: str) -> dict:
    resultado = {
        "respuesta_limpia": respuesta,
        "netlify_url": None,
        "netlify_error": None,
        "deployed": False
    }

    patron = r"===NETLIFY_DEPLOY===\s*SITE_NAME:\s*(.+?)\s*HTML:\s*([\s\S]*?)(?===END_DEPLOY===|\Z)"
    match = re.search(patron, respuesta, re.IGNORECASE | re.DOTALL)

    if not match:
        return resultado

    site_name = match.group(1).strip().lower().replace(" ", "-")
    html_content = match.group(2).strip()

    respuesta_limpia = re.sub(patron, "", respuesta, flags=re.IGNORECASE | re.DOTALL).strip()
    resultado["respuesta_limpia"] = respuesta_limpia or "✅ Página web generada y desplegada correctamente."

    deploy_result = deploy_a_netlify(site_name, html_content)

    if deploy_result["success"]:
        resultado["netlify_url"] = deploy_result["url"]
        resultado["deployed"] = True
    else:
        resultado["netlify_error"] = deploy_result["error"]

    return resultado
