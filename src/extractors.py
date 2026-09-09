"""
Módulo para extraer datos de elementos en Google Maps.
Separa la lógica de extracción del flujo principal.
"""

import re
import logging
from typing import Dict, Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)


# Selectores CSS con documentación clara
SELECTORS = {
    "results_list": 'div[role="feed"]',
    "result_item": 'div[role="feed"] > div > div[jsaction]',
    "business_name": 'h1[class*="DUwDvf"]',
    "rating": 'div[class*="F7nice"] span[aria-hidden="true"]',
    "reviews_count": 'div[class*="F7nice"] span[aria-label]',
    "category": 'button[jsaction*="category"]',
    "address": 'button[data-item-id="address"]',
    "phone": 'button[data-item-id*="phone"]',
    "website": 'a[data-item-id="authority"]',
    "open_status": 'div[class*="o0Svhf"]',
}

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


async def extract_business_data(page: Page) -> Dict[str, str]:
    """
    Extrae datos de un negocio desde la página abierta de Google Maps.

    Args:
        page: Página de Playwright

    Returns:
        Diccionario con datos del negocio
    """
    data: Dict[str, str] = {k: "" for k in FIELDNAMES}

    # Nombre del negocio
    try:
        el = await page.query_selector(SELECTORS["business_name"])
        if el:
            data["nombre"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo nombre: {e}")

    # Rating
    try:
        el = await page.query_selector(SELECTORS["rating"])
        if el:
            data["rating"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo rating: {e}")

    # Cantidad de reviews
    try:
        el = await page.query_selector(SELECTORS["reviews_count"])
        if el:
            aria = await el.get_attribute("aria-label") or ""
            numbers = re.findall(r"[\d,\.]+", aria)
            if numbers:
                data["cantidad_reviews"] = numbers[0].replace(",", "")
    except Exception as e:
        logger.debug(f"Error extrayendo cantidad de reviews: {e}")

    # Categoría
    try:
        el = await page.query_selector(SELECTORS["category"])
        if el:
            data["categoria"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo categoría: {e}")

    # Dirección
    try:
        el = await page.query_selector(SELECTORS["address"])
        if el:
            data["direccion"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo dirección: {e}")

    # Teléfono
    try:
        el = await page.query_selector(SELECTORS["phone"])
        if el:
            data["telefono"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo teléfono: {e}")

    # Sitio web
    try:
        el = await page.query_selector(SELECTORS["website"])
        if el:
            data["sitio_web"] = await el.get_attribute("href") or ""
    except Exception as e:
        logger.debug(f"Error extrayendo sitio web: {e}")

    # Estado (Abierto/Cerrado)
    try:
        el = await page.query_selector(SELECTORS["open_status"])
        if el:
            data["horario_estado"] = (await el.inner_text()).strip()
    except Exception as e:
        logger.debug(f"Error extrayendo estado: {e}")

    return data
