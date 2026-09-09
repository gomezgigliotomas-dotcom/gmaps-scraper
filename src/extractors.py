"""
Módulo para extraer datos de elementos en Google Maps.
Separa la lógica de extracción del flujo principal.
Los selectores CSS se reciben desde config (ver src/config.py).
"""

import re
import logging
from typing import Dict
from playwright.async_api import Page

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
            data["nombre"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo nombre: {e}")

    # Rating
    try:
        el = await page.query_selector(selectors["rating"])
        if el:
            data["rating"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo rating: {e}")

    # Cantidad de reviews
    try:
        el = await page.query_selector(selectors["reviews_count"])
        if el:
            aria = await el.get_attribute("aria-label") or ""
            numbers = re.findall(r"[\d,\.]+", aria)
            if numbers:
                data["cantidad_reviews"] = numbers[0].replace(",", "")
    except Exception as e:
        logger.debug(f"Error extrayendo cantidad de reviews: {e}")

    # Categoría
    try:
        el = await page.query_selector(selectors["category"])
        if el:
            data["categoria"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo categoría: {e}")

    # Dirección
    try:
        el = await page.query_selector(selectors["address"])
        if el:
            data["direccion"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo dirección: {e}")

    # Teléfono
    try:
        el = await page.query_selector(selectors["phone"])
        if el:
            data["telefono"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo teléfono: {e}")

    # Sitio web
    try:
        el = await page.query_selector(selectors["website"])
        if el:
            data["sitio_web"] = await el.get_attribute("href") or ""
    except Exception as e:
        logger.debug(f"Error extrayendo sitio web: {e}")

    # Estado (Abierto/Cerrado)
    try:
        el = await page.query_selector(selectors["open_status"])
        if el:
            data["horario_estado"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo estado: {e}")

    return data
