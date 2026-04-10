"""
Herramientas externas disponibles para todos los agentes:
- OpenStreetMap / Overpass API: buscar negocios por zona y categoría (gratis, sin API key)
- DuckDuckGo: búsqueda web en tiempo real (gratis, sin API key)
"""
import requests
from duckduckgo_search import DDGS

# Mapeo de términos en español a tags de OpenStreetMap
_OSM_TAGS = {
    "restaurante":  ("amenity", "restaurant"),
    "restaurantes": ("amenity", "restaurant"),
    "hotel":        ("tourism", "hotel"),
    "hoteles":      ("tourism", "hotel"),
    "hostal":       ("tourism", "hostel"),
    "clínica":      ("amenity", "clinic"),
    "clinica":      ("amenity", "clinic"),
    "hospital":     ("amenity", "hospital"),
    "farmacia":     ("amenity", "pharmacy"),
    "farmacias":    ("amenity", "pharmacy"),
    "café":         ("amenity", "cafe"),
    "cafetería":    ("amenity", "cafe"),
    "cafeteria":    ("amenity", "cafe"),
    "bar":          ("amenity", "bar"),
    "supermercado": ("shop", "supermarket"),
    "tienda":       ("shop", "convenience"),
    "banco":        ("amenity", "bank"),
    "dentista":     ("amenity", "dentist"),
    "veterinaria":  ("amenity", "veterinary"),
    "gimnasio":     ("leisure", "fitness_centre"),
    "gym":          ("leisure", "fitness_centre"),
    "panadería":    ("shop", "bakery"),
    "panaderia":    ("shop", "bakery"),
    "peluquería":   ("shop", "hairdresser"),
    "peluqueria":   ("shop", "hairdresser"),
    "salón":        ("shop", "hairdresser"),
    "salon":        ("shop", "hairdresser"),
    "taller":       ("shop", "car_repair"),
    "ferretería":   ("shop", "hardware"),
    "ferreteria":   ("shop", "hardware"),
    "sodas":        ("amenity", "restaurant"),
    "soda":         ("amenity", "restaurant"),
}


def _geocodificar(ubicacion: str) -> tuple[float, float] | None:
    """Obtiene lat/lon de un lugar usando Nominatim (OpenStreetMap)."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": ubicacion, "format": "json", "limit": 1},
            headers={"User-Agent": "VerticeDigital/1.0 (contacto@verticedigital.cr)"},
            timeout=6,
        )
        data = resp.json()
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None


def buscar_negocios_maps(consulta: str, ubicacion: str, radio_metros: int = 5000) -> dict:
    """
    Busca negocios usando OpenStreetMap + Overpass API.
    Completamente gratis, sin API key.
    Devuelve si el negocio tiene sitio web, teléfono y redes sociales.
    """
    # 1. Geocodificar la ubicación
    coords = _geocodificar(ubicacion)
    if not coords:
        return {"error": f"No se pudo encontrar la ubicación: {ubicacion}"}
    lat, lon = coords

    # 2. Determinar el tag OSM según la consulta
    consulta_lower = consulta.lower()
    osm_key, osm_val = None, None
    for termino, (key, val) in _OSM_TAGS.items():
        if termino in consulta_lower:
            osm_key, osm_val = key, val
            break

    # 3. Construir query Overpass
    radio_grados = radio_metros / 111000
    sur  = lat - radio_grados
    oeste = lon - radio_grados
    norte = lat + radio_grados
    este  = lon + radio_grados
    bbox = f"{sur},{oeste},{norte},{este}"

    if osm_key and osm_val:
        overpass_query = f"""
[out:json][timeout:15];
(
  node[{osm_key}={osm_val}]({bbox});
  way[{osm_key}={osm_val}]({bbox});
);
out body center 15;
"""
    else:
        # Búsqueda por nombre si no hay tag específico
        overpass_query = f"""
[out:json][timeout:15];
(
  node[name~"{consulta}",i]({bbox});
  way[name~"{consulta}",i]({bbox});
);
out body center 15;
"""

    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=overpass_query,
            timeout=8,
        )
        data = resp.json()

        resultados = []
        for elem in data.get("elements", [])[:15]:
            tags = elem.get("tags", {})
            nombre = tags.get("name")
            if not nombre:
                continue

            resultados.append({
                "nombre":    nombre,
                "tipo":      tags.get(osm_key or "amenity") or tags.get("shop") or tags.get("tourism"),
                "telefono":  tags.get("phone") or tags.get("contact:phone"),
                "web":       tags.get("website") or tags.get("contact:website"),
                "facebook":  tags.get("contact:facebook") or tags.get("facebook"),
                "instagram": tags.get("contact:instagram") or tags.get("instagram"),
                "direccion": tags.get("addr:street", "") + " " + tags.get("addr:housenumber", ""),
                "tiene_web": bool(tags.get("website") or tags.get("contact:website")),
            })

        return {
            "total":     len(resultados),
            "ubicacion": ubicacion,
            "sin_web":   sum(1 for r in resultados if not r["tiene_web"]),
            "resultados": resultados,
        }

    except Exception as e:
        return {"error": str(e)}


def buscar_en_web(consulta: str) -> dict:
    """Busca información actual en internet usando DuckDuckGo (gratis, sin API key)."""
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(consulta, max_results=8, region="cr-es"))

        resultados = [
            {
                "titulo":      r.get("title"),
                "url":         r.get("href"),
                "descripcion": r.get("body"),
            }
            for r in raw
        ]
        return {"total": len(resultados), "resultados": resultados}

    except Exception as e:
        return {"error": str(e)}


# ─── Definiciones de herramientas para la API de Anthropic ───────────────────

TOOLS = [
    {
        "name": "buscar_negocios_maps",
        "description": (
            "Busca negocios reales en OpenStreetMap por zona y categoría. "
            "Devuelve nombre, teléfono, sitio web, Facebook, Instagram y si tienen presencia digital. "
            "Úsala para encontrar restaurantes, hoteles, clínicas, tiendas u otros negocios en Costa Rica. "
            "Especialmente útil para identificar negocios sin sitio web (prospectos de venta)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "Tipo de negocio (ej: 'restaurantes', 'hoteles', 'clínicas dentales', 'sodas')"
                },
                "ubicacion": {
                    "type": "string",
                    "description": "Ciudad o zona (ej: 'Liberia, Guanacaste, Costa Rica')"
                },
                "radio_metros": {
                    "type": "integer",
                    "description": "Radio de búsqueda en metros (default 5000)",
                    "default": 5000
                }
            },
            "required": ["consulta", "ubicacion"]
        }
    },
    {
        "name": "buscar_en_web",
        "description": (
            "Busca información actual en internet. Úsala para verificar sitios web, "
            "redes sociales, contactos de empresas, precios de competencia, "
            "noticias recientes o cualquier dato que necesite ser actual."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "Términos de búsqueda (ej: 'Restaurante Don Carlos Liberia sitio web')"
                }
            },
            "required": ["consulta"]
        }
    }
]
