"""
Módulo para extraer datos de elementos en Google Maps.
Separa la lógica de extracción del flujo principal.
Los selectores CSS se reciben desde config (ver src/config.py).
"""

import re
import logging
from typing import Dict, Optional
from playwright.async_api import Page, ElementHandle

logger = logging.getLogger(__name__)


FIELDNAMES = [
    "nombre",
    "categoria",
    "rating",
    "cantidad_reviews",
    "direccion",
    "telefono",
    "sitio_web",
    "horario_estado",
]

# Google Maps mete iconos de su fuente propia (Material Symbols) directamente
# como texto en varios botones (flecha desplegable, icono de telefono, etc.).
# Esos glifos viven en la Private Use Area de Unicode (U+E000-U+F8FF) y no
# son texto real — se descartan de cualquier campo extraido.
_PRIVATE_USE_AREA = re.compile("[-]")

# U+202F (narrow no-break space) y U+00A0 (non-breaking space) aparecen en
# horarios ("8:30 p.m.") en vez de un espacio normal; se normalizan a " ".
_WHITESPACE_VARIANTS = re.compile("[  ]")


def _clean_text(text: Optional[str]) -> str:
    """Limpia texto extraido de Google Maps: iconos de fuente, saltos de
    linea espurios y variantes de espacio en blanco, sin tocar el contenido
    real (acentos, enie, etc.)."""
    if not text:
        return ""
    text = _PRIVATE_USE_AREA.sub("", text)
    text = _WHITESPACE_VARIANTS.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def _text_from_aria_or_inner(
    el: ElementHandle, prefix_to_strip: str = ""
) -> str:
    """
    Prefiere el aria-label del elemento (formato estable: "Direccion: ...",
    "Telefono: ...") sobre inner_text(), que suele arrastrar iconos de
    fuente concatenados como si fueran texto. Cae a inner_text() si no hay
    aria-label.
    """
    aria = await el.get_attribute("aria-label")
    if aria:
        text = _clean_text(aria)
        if prefix_to_strip and text.startswith(prefix_to_strip):
            text = text[len(prefix_to_strip):].strip()
        return text
    return _clean_text(await el.inner_text())


async def extract_business_data(page: Page, selectors: Dict[str, str]) -> Dict[str, str]:
    """
    Extrae datos de un negocio desde la página abierta de Google Maps.

    Args:
        page: Página de Playwright
        selectors: Diccionario de selectores CSS (desde config)

    Returns:
        Diccionario con datos del negocio
    """
    data: Dict[str, str] = {k: "" for k in FIELDNAMES}

    # Nombre del negocio
    try:
        el = await page.query_selector(selectors["business_name"])
        if el:
            data["nombre"] = _clean_text(await el.inner_text())
    except Exception as e:
        logger.debug(f"Error extrayendo nombre: {e}")

    # Rating
    try:
        el = await page.query_selector(selectors["rating"])
        if el:
            data["rating"] = _clean_text(await el.inner_text())
    except Exception as e:
        logger.debug(f"Error extrayendo rating: {e}")

    # Cantidad de reviews. El contenedor de rating también incluye un
    # span de "estrellas visuales" con aria-label del tipo "4.9 estrellas"
    # — tiene un número, pero NO es el conteo de reseñas. Se descarta
    # explícitamente para no confundirlo con el conteo real.
    try:
        el = await page.query_selector(selectors["reviews_count"])
        if el:
            aria = await el.get_attribute("aria-label") or ""
            if not re.search(r"estrella|star", aria, re.IGNORECASE):
                numbers = re.findall(r"[\d.,]+", aria)
                if numbers:
                    data["cantidad_reviews"] = numbers[0].replace(",", "")
    except Exception as e:
        logger.debug(f"Error extrayendo cantidad de reviews: {e}")

    # Categoría
    try:
        el = await page.query_selector(selectors["category"])
        if el:
            data["categoria"] = _clean_text(await el.inner_text())
    except Exception as e:
        logger.debug(f"Error extrayendo categoría: {e}")

    # Dirección — el botón trae un ícono como primer "carácter" en
    # inner_text(); el aria-label ("Dirección: ...") viene limpio.
    try:
        el = await page.query_selector(selectors["address"])
        if el:
            data["direccion"] = await _text_from_aria_or_inner(el, prefix_to_strip="Dirección:")
    except Exception as e:
        logger.debug(f"Error extrayendo dirección: {e}")

    # Teléfono — mismo caso que dirección.
    try:
        el = await page.query_selector(selectors["phone"])
        if el:
            data["telefono"] = await _text_from_aria_or_inner(el, prefix_to_strip="Teléfono:")
    except Exception as e:
        logger.debug(f"Error extrayendo teléfono: {e}")

    # Sitio web
    try:
        el = await page.query_selector(selectors["website"])
        if el:
            data["sitio_web"] = await el.get_attribute("href") or ""
    except Exception as e:
        logger.debug(f"Error extrayendo sitio web: {e}")

    # Estado (Abierto/Cerrado) — termina con el ícono de flecha desplegable
    # concatenado en inner_text(); se limpia igual que el resto.
    try:
        el = await page.query_selector(selectors["open_status"])
        if el:
            data["horario_estado"] = _clean_text(await el.inner_text())
    except Exception as e:
        logger.debug(f"Error extrayendo estado: {e}")

    return data
