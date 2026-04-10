"""
Memoria persistente para sesiones de chat.
Guarda el historial en SQLite para que los agentes recuerden entre reinicios.
"""
import sqlite3
import json
import os

DB_PATH = os.environ.get("MEMORIA_DB", "vertice_memoria.db")

def _conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            session_id TEXT NOT NULL,
            rol        TEXT NOT NULL,
            contenido  TEXT NOT NULL,
            ts         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def cargar_historial(session_id: str, limite: int = 40) -> list:
    """Carga los últimos `limite` mensajes de una sesión."""
    conn = _conectar()
    rows = conn.execute(
        "SELECT rol, contenido FROM historial WHERE session_id=? ORDER BY ts DESC LIMIT ?",
        (session_id, limite)
    ).fetchall()
    conn.close()
    # Revertir para orden cronológico
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def guardar_mensajes(session_id: str, mensajes: list):
    """Guarda una lista de {role, content} en la base de datos."""
    conn = _conectar()
    conn.executemany(
        "INSERT INTO historial (session_id, rol, contenido) VALUES (?, ?, ?)",
        [(session_id, m["role"], m["content"]) for m in mensajes]
    )
    conn.commit()
    conn.close()
