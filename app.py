import os
import uuid
from flask import Flask, request, jsonify, render_template_string
from agents.base import responder, responder_paralelo
from agents.router import detectar_combinacion
from agents.telegram_service import enviar_aprobacion, notificar

app = Flask(__name__)

sesiones = {}
aprobaciones_pendientes = {}
archivos_html = {}

HTML_CHAT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vértice Digital — Panel de Agentes</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600&family=Inter:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; background: #0f0f1a; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .chat-container { width: 100%; max-width: 680px; background: #1a1a2e; border-radius: 20px; border: 1px solid #2a2a4a; display: flex; flex-direction: column; height: 92vh; }
        .header { padding: 20px 24px; border-bottom: 1px solid #2a2a4a; }
        .header h1 { font-family: 'Poppins', sans-serif; font-size: 18px; color: #fff; font-weight: 600; }
        .header p { font-size: 12px; color: #6c63ff; margin-top: 2px; }
        .agents-bar { display: flex; gap: 8px; padding: 10px 24px; border-bottom: 1px solid #2a2a4a; flex-wrap: wrap; }
        .agent-pill { font-size: 11px; padding: 4px 10px; border-radius: 20px; border: 1px solid #2a2a4a; color: #888; cursor: pointer; transition: all 0.2s; }
        .agent-pill:hover, .agent-pill.active { background: #6c63ff; color: #fff; border-color: #6c63ff; }
        .messages { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 14px; }
        .messages::-webkit-scrollbar { width: 4px; }
        .messages::-webkit-scrollbar-thumb { background: #2a2a4a; border-radius: 4px; }
        .msg { max-width: 85%; padding: 12px 16px; border-radius: 14px; font-size: 14px; line-height: 1.6; }
        .msg.user { align-self: flex-end; background: #6c63ff; color: #fff; border-radius: 14px 14px 4px 14px; }
        .msg.bot { align-self: flex-start; background: #252540; color: #e0e0e0; border-radius: 14px 14px 14px 4px; border: 1px solid #2a2a4a; }
        .msg.bot-paralelo  { align-self: flex-start; background: #1a2a1a; color: #90ee90; border-radius: 14px 14px 14px 4px; border: 1px solid #2a4a2a; }
        .msg.bot-paralelo2 { align-self: flex-start; background: #2a1a2a; color: #da90ee; border-radius: 14px 14px 14px 4px; border: 1px solid #4a2a4a; }
        .msg.bot-paralelo3 { align-self: flex-start; background: #2a2a1a; color: #eeda90; border-radius: 14px 14px 14px 4px; border: 1px solid #4a4a2a; }
        .msg.bot-error { align-self: flex-start; background: #2a1a1a; color: #ff6b6b; border-radius: 14px 14px 14px 4px; border: 1px solid #4a2a2a; }
        .agente-tag { font-size: 10px; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
        .msg.bot .agente-tag { color: #6c63ff; }
        .msg.bot-paralelo  .agente-tag { color: #90ee90; }
        .msg.bot-paralelo2 .agente-tag { color: #da90ee; }
        .msg.bot-paralelo3 .agente-tag { color: #eeda90; }
        .msg.bot-error .agente-tag { color: #ff6b6b; }
        .msg pre { background: #0f0f1a; padding: 10px; border-radius: 8px; overflow-x: auto; font-size: 12px; margin-top: 8px; white-space: pre-wrap; }
        .aprobacion-banner { background: #2a1a0a; border: 1px solid #ff9800; border-radius: 10px; padding: 10px 14px; font-size: 12px; color: #ff9800; margin-top: 8px; }
        .typing { font-size: 12px; color: #555; padding: 0 24px 8px; font-style: italic; }
        .input-area { padding: 16px 24px; border-top: 1px solid #2a2a4a; display: flex; gap: 8px; }
        .input-area input { flex: 1; padding: 12px 16px; background: #252540; border: 1px solid #2a2a4a; border-radius: 24px; font-size: 14px; color: #fff; outline: none; font-family: 'Inter', sans-serif; }
        .input-area input:focus { border-color: #6c63ff; }
        .input-area input::placeholder { color: #555; }
        .input-area button { padding: 12px 20px; background: #6c63ff; color: white; border: none; border-radius: 24px; cursor: pointer; font-size: 14px; font-weight: 500; font-family: 'Inter', sans-serif; transition: background 0.2s; }
        .input-area button:hover { background: #5a52cc; }
        .input-area button:disabled { background: #3a3a5a; cursor: not-allowed; }
        .modo-paralelo { font-size: 11px; color: #555; padding: 4px 24px; text-align: right; }
    </style>
</head>
<body>
<div class="chat-container">
    <div class="header">
        <h1>Vértice Digital — Panel de Agentes</h1>
        <p>Tu equipo de IA trabajando para vos</p>
    </div>
    <div class="agents-bar">
        <span class="agent-pill active" data-agente="auto">Auto</span>
        <span class="agent-pill" data-agente="asistente">Asistente</span>
        <span class="agent-pill" data-agente="marketing">Marketing</span>
        <span class="agent-pill" data-agente="ventas">Ventas</span>
        <span class="agent-pill" data-agente="desarrollador">Desarrollador</span>
        <span class="agent-pill" data-agente="soporte">Soporte</span>
    </div>
    <div class="messages" id="messages">
        <div class="msg bot">
            <div class="agente-tag">Asistente — Vértice Digital</div>
            Bienvenido Allan. ¿Qué hacemos hoy? Podés escribirme directamente o seleccionar un agente específico arriba.
        </div>
    </div>
    <div class="typing" id="typing"></div>
    <div class="modo-paralelo" id="modo-label"></div>
    <div class="input-area">
        <input type="text" id="input" placeholder="Decile algo a tu equipo..."/>
        <button id="btn-enviar">Enviar</button>
    </div>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {
    var sessionId = Math.random().toString(36).substr(2, 9);
    var agenteSeleccionado = 'auto';
    var enviando = false;

    document.querySelectorAll('.agent-pill').forEach(function(pill) {
        pill.addEventListener('click', function() {
            var agente = this.getAttribute('data-agente');
            agenteSeleccionado = agente;
            document.querySelectorAll('.agent-pill').forEach(function(p) { p.classList.remove('active'); });
            this.classList.add('active');
            document.getElementById('modo-label').textContent = agente === 'desarrollador' ? 'Modo paralelo: Desarrollador + Disenador' : '';
        });
    });

    document.getElementById('input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') enviar();
    });

    document.getElementById('btn-enviar').addEventListener('click', enviar);

    async function enviar() {
        if (enviando) return;
        var inputEl = document.getElementById('input');
        var btn = document.getElementById('btn-enviar');
        var msg = inputEl.value.trim();
        if (!msg) return;

        enviando = true;
        btn.disabled = true;
        inputEl.value = '';
        agregarMensaje(msg, 'user', '');
        document.getElementById('typing').textContent = 'Tu equipo esta trabajando...';

        try {
            var res = await fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mensaje: msg, session_id: sessionId, agente: agenteSeleccionado})
            });

            if (!res.ok) {
                var errText = await res.text();
                throw new Error('Error ' + res.status + ': ' + errText);
            }

            var data = await res.json();
            document.getElementById('typing').textContent = '';

            if (data.html_file_id) {
                var enlace = document.createElement('a');
                enlace.href = '/descargar/' + data.html_file_id;
                enlace.download = 'vertice-digital.html';
                enlace.style.cssText = 'display:inline-block;margin-top:10px;padding:10px 20px;background:#6c63ff;color:#fff;border-radius:20px;text-decoration:none;font-size:13px;font-weight:500;';
                enlace.textContent = 'Descargar index.html';
                var msgDiv = document.createElement('div');
                msgDiv.className = 'msg bot';
                msgDiv.innerHTML = '<div class="agente-tag">Lead Developer</div>Pagina lista para descargar:';
                msgDiv.appendChild(enlace);
                document.getElementById('messages').appendChild(msgDiv);
                var m = document.getElementById('messages');
                m.scrollTop = m.scrollHeight;
            } else if (data.modo === 'paralelo' && data.resultados) {
                var colores = ['bot', 'bot-paralelo', 'bot-paralelo2', 'bot-paralelo3'];
                var idx = 0;
                Object.keys(data.resultados).forEach(function(key) {
                    var val = data.resultados[key];
                    agregarMensaje(val.respuesta, colores[idx % colores.length], val.nombre);
                    idx++;
                });
            } else {
                agregarMensaje(data.respuesta || 'Sin respuesta', 'bot', data.nombre_agente || 'Agente');
            }

            if (data.telegram_enviado) {
                var banner = document.createElement('div');
                banner.className = 'aprobacion-banner';
                banner.textContent = 'Enviado a Telegram para aprobacion';
                document.getElementById('messages').lastChild.appendChild(banner);
            }

        } catch (err) {
            document.getElementById('typing').textContent = '';
            agregarMensaje('Error: ' + err.message, 'bot-error', 'Sistema');
        } finally {
            enviando = false;
            btn.disabled = false;
            document.getElementById('input').focus();
        }
    }

    function agregarMensaje(texto, tipo, agente) {
        var div = document.createElement('div');
        div.className = 'msg ' + tipo;
        var textoStr = texto ? String(texto) : '';
        var tag = agente ? '<div class="agente-tag">' + agente + '</div>' : '';
        var textoFormateado = textoStr.replace(/```([\s\S]*?)```/g, '<pre>$1</pre>').replace(/\n/g, '<br>');
        div.innerHTML = tag + textoFormateado;
        var msgs = document.getElementById('messages');
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
    }
});
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
        return jsonify({
            "agente": "sistema",
            "nombre_agente": "Sistema",
            "respuesta": f"[Error interno del servidor: {str(e)}]",
            "modo": "normal",
            "telegram_enviado": False
        }), 500

    sesiones[session_id].append({"role": "user", "content": mensaje})
    sesiones[session_id].append({"role": "assistant", "content": resultado["respuesta"]})
    if len(sesiones[session_id]) > 20:
        sesiones[session_id] = sesiones[session_id][-20:]

    # Detectar si necesita aprobación (posts de redes sociales)
    telegram_enviado = False
    palabras_aprobacion = ['post', 'publicación', 'instagram', 'facebook', 'tiktok', 'publicar']
    if any(p in mensaje.lower() for p in palabras_aprobacion):
        id_aprobacion = str(uuid.uuid4())[:8].upper()
        aprobaciones_pendientes[id_aprobacion] = {
            "contenido": resultado["respuesta"],
            "tipo": "Post redes sociales",
            "session_id": session_id
        }
        enviar_aprobacion("Post redes sociales", resultado["respuesta"], id_aprobacion)
        telegram_enviado = True

    resultado["telegram_enviado"] = telegram_enviado

    # Detectar si la respuesta contiene un archivo HTML para descargar
    respuesta = resultado.get("respuesta", "")
    if "===HTML_FILE===" in respuesta and "===END_HTML===" in respuesta:
        inicio = respuesta.index("===HTML_FILE===") + len("===HTML_FILE===")
        fin = respuesta.index("===END_HTML===")
        html_code = respuesta[inicio:fin].strip()
        file_id = str(uuid.uuid4())[:8].upper()
        archivos_html[file_id] = html_code
        resultado["html_file_id"] = file_id
        resultado["respuesta"] = "✅ Página web lista. Hacé clic en el botón para descargar el archivo HTML."

    return jsonify(resultado)

@app.route('/descargar/<file_id>')
def descargar(file_id):
    if file_id not in archivos_html:
        return "Archivo no encontrado", 404
    html = archivos_html[file_id]
    from flask import Response
    return Response(
        html,
        mimetype='text/html',
        headers={'Content-Disposition': f'attachment; filename=vertice-digital.html'}
    )

# FIX 3: /chat/paralelo ahora pasa combinacion correctamente
@app.route('/chat/paralelo', methods=['POST'])
def chat_paralelo():
    data = request.json
    mensaje = data.get('mensaje', '').strip()
    session_id = data.get('session_id', 'default')
    if not mensaje:
        return jsonify({"error": "Mensaje vacío"}), 400

    combinacion = detectar_combinacion(mensaje) or {
        "agentes": ["desarrollador", "disenador"],
        "nombre": "default",
        "descripcion": "Desarrollador + Diseñador"
    }

    try:
        resultado = responder_paralelo(mensaje, combinacion)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    notificar(f"⚡ Tarea paralela completada:\n{combinacion['descripcion']} trabajaron en: {mensaje[:80]}...")
    return jsonify(resultado)

@app.route('/aprobar/<id_aprobacion>', methods=['POST'])
def aprobar(id_aprobacion):
    if id_aprobacion not in aprobaciones_pendientes:
        return jsonify({"error": "ID no encontrado"}), 404
    item = aprobaciones_pendientes.pop(id_aprobacion)
    notificar(f"✅ Aprobado: {item['tipo']}\nID: {id_aprobacion}\nListo para publicar.")
    return jsonify({"status": "aprobado", "contenido": item["contenido"]})

@app.route('/rechazar/<id_aprobacion>', methods=['POST'])
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
    texto = data['message'].get('text', '').strip()
    partes = texto.split(' ', 2)
    comando = partes[0].lower()
    if comando == 'aprobar' and len(partes) >= 2:
        id_ap = partes[1].upper()
        if id_ap in aprobaciones_pendientes:
            aprobaciones_pendientes.pop(id_ap)
            notificar(f"✅ Contenido <b>{id_ap}</b> aprobado. Listo para publicar.")
        else:
            notificar(f"⚠️ ID {id_ap} no encontrado o ya procesado.")
    elif comando == 'rechazar' and len(partes) >= 2:
        id_ap = partes[1].upper()
        if id_ap in aprobaciones_pendientes:
            aprobaciones_pendientes.pop(id_ap)
            notificar(f"❌ Contenido <b>{id_ap}</b> rechazado.")
    elif comando == 'editar' and len(partes) >= 3:
        id_ap = partes[1].upper()
        feedback = partes[2]
        if id_ap in aprobaciones_pendientes:
            notificar(f"✏️ Feedback recibido para <b>{id_ap}</b>:\n{feedback}\nRevisando...")
    elif comando == 'pendientes':
        if aprobaciones_pendientes:
            lista = '\n'.join([f"• {k}: {v['tipo']}" for k, v in aprobaciones_pendientes.items()])
            notificar(f"📋 Pendientes de aprobación:\n{lista}")
        else:
            notificar("✅ No hay nada pendiente de aprobación.")
    return jsonify({"ok": True})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "empresa": "Vértice Digital", "agentes": 6})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
