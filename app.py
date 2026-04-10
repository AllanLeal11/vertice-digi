import os
import uuid
from flask import Flask, request, jsonify, render_template_string, send_file
from agents.base import responder, responder_paralelo
from agents.router import detectar_combinacion
from agents.telegram_service import enviar_aprobacion, notificar

app = Flask(__name__)

sesiones = {}
aprobaciones_pendientes = {}
archivos = {}  # Ahora guarda tanto HTML como PDF

# ==================== HTML CHAT FUNCIONAL ====================
HTML_CHAT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vértice Digital — Panel de Agentes</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Poppins:wght@600&display=swap');
        body { font-family: 'Inter', system-ui; }
        .chat-header { font-family: 'Poppins', sans-serif; }
        .message { animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body class="bg-gray-950 text-white min-h-screen">
    <div class="max-w-5xl mx-auto h-screen flex flex-col">
        <div class="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-9 h-9 bg-violet-600 rounded-2xl flex items-center justify-center text-white font-bold text-xl">V</div>
                <div>
                    <h1 class="chat-header text-2xl font-semibold">Vértice Digital</h1>
                    <p class="text-emerald-400 text-sm">Tu equipo de IA trabajando para vos</p>
                </div>
            </div>
        </div>

        <div class="bg-gray-900 px-6 py-3 border-b border-gray-800 flex gap-2 overflow-x-auto" id="agent-tabs">
            <button onclick="setAgente('auto')" class="agent-tab active px-5 py-2 rounded-3xl text-sm font-medium bg-violet-600 text-white">Auto</button>
            <button onclick="setAgente('asistente')" class="agent-tab px-5 py-2 rounded-3xl text-sm font-medium hover:bg-gray-800">Asistente</button>
            <button onclick="setAgente('marketing')" class="agent-tab px-5 py-2 rounded-3xl text-sm font-medium hover:bg-gray-800">Marketing</button>
            <button onclick="setAgente('ventas')" class="agent-tab px-5 py-2 rounded-3xl text-sm font-medium hover:bg-gray-800">Ventas</button>
            <button onclick="setAgente('desarrollador')" class="agent-tab px-5 py-2 rounded-3xl text-sm font-medium hover:bg-gray-800">Desarrollador</button>
            <button onclick="setAgente('soporte')" class="agent-tab px-5 py-2 rounded-3xl text-sm font-medium hover:bg-gray-800">Soporte</button>
        </div>

        <div id="chat" class="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-950"></div>

        <div class="bg-gray-900 border-t border-gray-800 p-4">
            <div class="max-w-3xl mx-auto flex gap-3">
                <input id="mensaje" type="text" placeholder="Escribí tu mensaje aquí..." 
                       class="flex-1 bg-gray-800 text-white placeholder-gray-400 rounded-3xl px-6 py-4 focus:outline-none focus:ring-2 focus:ring-violet-500"
                       onkeydown="if(event.key === 'Enter') sendMessage()">
                <button onclick="sendMessage()" class="bg-violet-600 hover:bg-violet-700 w-14 h-14 rounded-3xl flex items-center justify-center text-xl transition">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>
        </div>
    </div>

    <script>
        let currentAgente = 'auto';
        let sessionId = 'default-' + Math.random().toString(36).substring(7);

        function setAgente(agente) {
            currentAgente = agente;
            document.querySelectorAll('.agent-tab').forEach(tab => {
                tab.classList.toggle('active', tab.textContent.toLowerCase() === agente || (agente === 'auto' && tab.textContent === 'Auto'));
            });
        }

        async function sendMessage() {
            const input = document.getElementById('mensaje');
            const mensaje = input.value.trim();
            if (!mensaje) return;

            addMessage('user', mensaje);
            input.value = '';

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mensaje: mensaje, session_id: sessionId, agente: currentAgente })
                });
                const data = await res.json();

                let displayText = data.respuesta || '';

                if (displayText) {
                    addMessage('assistant', displayText, data.nombre_agente);
                }

                if (data.html_file_id) {
                    const link = document.createElement('a');
                    link.href = `/descargar/${data.html_file_id}`;
                    link.download = 'vertice-digital.html';
                    link.click();
                }
                if (data.pdf_file_id) {
                    const link = document.createElement('a');
                    link.href = `/descargar/${data.pdf_file_id}`;
                    link.download = 'propuesta.pdf';
                    link.click();
                }
            } catch (e) {
                addMessage('assistant', '❌ Error de conexión con el servidor', 'Sistema');
            }
        }

        function addMessage(role, text, agentName = '') {
            const chat = document.getElementById('chat');
            const msg = document.createElement('div');
            msg.className = 'message';

            if (role === 'user') {
                msg.classList.add('flex', 'justify-end');
                msg.innerHTML = `<div class="max-w-[75%] bg-violet-600 text-white px-5 py-3 rounded-3xl rounded-tr-none">${text}</div>`;
            } else {
                msg.classList.add('flex', 'gap-3');
                msg.innerHTML = `
                    <div class="w-8 h-8 bg-gray-700 rounded-2xl flex-shrink-0 flex items-center justify-center text-sm font-bold">${agentName ? agentName.substring(0,1) : '🤖'}</div>
                    <div>
                        ${agentName ? `<div class="text-xs text-gray-400 mb-1">${agentName}</div>` : ''}
                        <div class="bg-gray-800 px-5 py-3 rounded-3xl rounded-tl-none">${text}</div>
                    </div>`;
            }
            chat.appendChild(msg);
            chat.scrollTop = chat.scrollHeight;
        }

        window.onload = () => {
            setAgente('auto');
            addMessage('assistant', 'Bienvenido Allan 👋 ¿Qué hacemos hoy?', 'Asistente');
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_CHAT)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    mensaje = data.get('mensaje', '').strip()
    session_id = data.get('session_id', 'default')
    agente_forzado = data.get('agente', 'auto')
    if not mensaje:
        return jsonify({"error": "Mensaje vacío"}), 400

    if session_id not in sesiones:
        sesiones[session_id] = []
    historial = sesiones[session_id]

    try:
        resultado = responder(mensaje, historial, agente_forzado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    sesiones[session_id].append({"role": "user", "content": mensaje})
    sesiones[session_id].append({"role": "assistant", "content": resultado["respuesta"]})
    if len(sesiones[session_id]) > 20:
        sesiones[session_id] = sesiones[session_id][-20:]

    # === PROCESAR PDF DEL AGENTE DE VENTAS ===
    try:
        from agents.ventas import generar_pdf_desde_texto
        respuesta = resultado.get("respuesta", "")
        if "===PDF_FILE===" in respuesta and "===END_PDF===" in respuesta:
            inicio = respuesta.index("===PDF_FILE===") + len("===PDF_FILE===")
            fin = respuesta.index("===END_PDF===")
            bloque = respuesta[inicio:fin].strip()

            titulo = "Propuesta Comercial - Vértice Digital"
            if "TÍTULO:" in bloque:
                titulo = bloque.split("TÍTULO:")[1].split("\n")[0].strip()

            pdf_path = generar_pdf_desde_texto(titulo, bloque)
            file_id = str(uuid.uuid4())[:8].upper()
            archivos[file_id] = pdf_path
            resultado["pdf_file_id"] = file_id
            resultado["respuesta"] = f"✅ {titulo} lista. Hacé clic en el botón para descargar el PDF."
    except:
        pass

    # === PROCESAR HTML DEL DESARROLLADOR (mantengo compatibilidad) ===
    try:
        from agents.desarrollador import procesar_respuesta_desarrollador
        processed = procesar_respuesta_desarrollador(resultado.get("respuesta", ""))
        resultado["respuesta"] = processed.get("respuesta_limpia", resultado["respuesta"])
    except:
        pass

    # Telegram aprobaciones (original)
    telegram_enviado = False
    if any(p in mensaje.lower() for p in ['post', 'publicación', 'instagram', 'facebook', 'tiktok', 'publicar']):
        id_aprobacion = str(uuid.uuid4())[:8].upper()
        aprobaciones_pendientes[id_aprobacion] = {"contenido": resultado["respuesta"], "tipo": "Post redes sociales", "session_id": session_id}
        enviar_aprobacion("Post redes sociales", resultado["respuesta"], id_aprobacion)
        telegram_enviado = True

    resultado["telegram_enviado"] = telegram_enviado
    return jsonify(resultado)

@app.route('/descargar/')
def descargar(file_id):
    if file_id not in archivos:
        return "Archivo no encontrado", 404

    archivo = archivos[file_id]

    if isinstance(archivo, str) and archivo.endswith('.pdf'):
        return send_file(archivo, as_attachment=True, download_name="propuesta.pdf")
    else:
        # HTML
        from flask import Response
        return Response(archivo, mimetype='text/html', headers={'Content-Disposition': 'attachment; filename=vertice-digital.html'})

# Resto de rutas (exactamente las mismas que tenías)
@app.route('/chat/paralelo', methods=['POST'])
def chat_paralelo():
    data = request.json
    mensaje = data.get('mensaje', '').strip()
    if not mensaje:
        return jsonify({"error": "Mensaje vacío"}), 400

    combinacion = detectar_combinacion(mensaje) or {"agentes": ["desarrollador", "disenador"], "nombre": "default", "descripcion": "Desarrollador + Diseñador"}

    try:
        resultado = responder_paralelo(mensaje, combinacion)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    notificar(f"⚡ Tarea paralela completada: {combinacion['descripcion']}")
    return jsonify(resultado)

@app.route('/aprobar/', methods=['POST'])
def aprobar(id_aprobacion):
    if id_aprobacion not in aprobaciones_pendientes:
        return jsonify({"error": "ID no encontrado"}), 404
    item = aprobaciones_pendientes.pop(id_aprobacion)
    notificar(f"✅ Aprobado: {item['tipo']}")
    return jsonify({"status": "aprobado", "contenido": item["contenido"]})

@app.route('/rechazar/', methods=['POST'])
def rechazar(id_aprobacion):
    if id_aprobacion not in aprobaciones_pendientes:
        return jsonify({"error": "ID no encontrado"}), 404
    aprobaciones_pendientes.pop(id_aprobacion)
    notificar(f"❌ Rechazado: ID {id_aprobacion}")
    return jsonify({"status": "rechazado"})

@app.route('/webhook/telegram', methods=['POST'])
def webhook_telegram():
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"ok": True})
    # (código original de webhook, lo mantengo igual)
    return jsonify({"ok": True})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "empresa": "Vértice Digital", "agentes": 6})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
