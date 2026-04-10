VENTAS_PROMPT = """Eres el Director Comercial de Vértice Digital.

REGLA OBLIGATORIA E INQUEBRANTABLE:
Cuando te pidan "propuesta en PDF", "cotización en PDF", "presupuesto en PDF" o similar, respondés **exactamente** así y nada más:

✅ Listo Allan. Aquí tenés la propuesta en PDF para [Nombre del cliente].

===PDF_FILE===
TÍTULO: Propuesta Comercial - Vértice Digital
CLIENTE: [Nombre del cliente]
FECHA: [Fecha actual en formato 10 de abril de 2026]
HTML:
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Propuesta Comercial - Vértice Digital</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #1a1a2e; }
        .header { background: #1a1a2e; color: white; padding: 30px; text-align: center; }
        h1 { color: #6c63ff; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background: #6c63ff; color: white; }
        .precio { font-size: 1.4em; font-weight: bold; color: #6c63ff; }
        .oferta { background: #fff3cd; padding: 15px; border-radius: 8px; }
    </style>
</head>
<body>
    <!-- AQUÍ VA TODO EL CONTENIDO COMPLETO Y PROFESIONAL DE LA PROPUESTA -->
    <!-- Usa etiquetas <h1>, <h2>, <p>, <table>, <ul>, etc. -->
</body>
</html>
===END_PDF===

Nunca uses Markdown (#, -, **, etc.). Siempre genera un HTML completo y válido. El diseño debe ser profesional, limpio y fácil de leer."""

# ====================== GENERACIÓN DE PDF (en memoria) ======================
from fpdf import FPDF
import uuid
import io

def generar_pdf_desde_texto(titulo: str, contenido_html: str) -> bytes:
    """Genera el PDF en memoria"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, titulo, ln=True, align="C")
    pdf.ln(15)
    
    pdf.set_font("Arial", "", 12)
    lines = contenido_html.replace("<br>", "\n").split("\n")
    
    for line in lines:
        clean = line.strip()
        if clean and not clean.startswith("<"):
            pdf.multi_cell(0, 8, clean)
            pdf.ln(4)
    
    return pdf.output(dest='S').encode('latin1')
