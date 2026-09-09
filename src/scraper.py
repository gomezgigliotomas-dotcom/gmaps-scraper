"""
Google Maps Business Scraper - Módulo principal de scraping.
Contiene la lógica de navegación y scroll en Google Maps.
"""

import asyncio
import logging
from typing import List, Dict
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from playwright.async_api import Page

from .extractors import extract_business_data, FIELDNAMES

logger = logging.getLogger(__name__)


async def scroll_results(page: Page, max_results: int) -> None:
    """
    Scrollea la lista de resultados para cargar más items.

    Args:
        page: Página de Playwright
        max_results: Máximo número de resultados a cargar
    """
    results_list_selector = 'div[role="feed"]'
    result_item_selector = 'div[role="feed"] > div > div[jsaction]'
    end_message_selector = 'span[class*="HlvSq"]'

    feed = await page.query_selector(results_list_selector)
    if not feed:
        logger.warning("No se encontró el panel de resultados")
        return

    last_count = 0
    stall_count = 0

    while True:
        items = await page.query_selector_all(result_item_selector)
        current_count = len(items)

        if current_count >= max_results:
            logger.info(f"Alcanzado límite de {max_results} resultados")
            break

        # Detectar si no hay más items (página se estancó)
        if current_count == last_count:
            stall_count += 1
            if stall_count >= 3:
                logger.info(f"Scroll estancado en {current_count} items")
                break
        else:
            stall_count = 0

        last_count = current_count
        logger.debug(f"Items cargados: {current_count}")

        # Scroll hacia abajo
        await feed.evaluate("el => el.scrollBy(0, 1000)")
        await page.wait_for_timeout(800)

        # Verificar si alcanzamos el final
        end_msg = await page.query_selector(end_message_selector)
        if end_msg:
            logger.info("Se alcanzó el final de los resultados")
            break


async def scrape(
    query: str,
    location: str,
    max_results: int,
    output_file: str,
    headless: bool,
) -> List[Dict[str, str]]:
    """
    Realiza el scraping de negocios en Google Maps.

    Args:
        query: Término de búsqueda (ej: "dentistas")
        location: Ubicación (ej: "Buenos Aires")
        max_results: Máximo de resultados a extraer
        output_file: Path del archivo CSV de salida
        headless: Si True, ejecuta sin mostrar navegador

    Returns:
        Lista de diccionarios con datos de negocios
    """
    search_term = f"{query} en {location}"
    results: List[Dict[str, str]] = []

    logger.info(f"Iniciando scraping: {search_term}")
    logger.info(f"Máximo de resultados: {max_results}")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                locale="es-AR",
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()

            # Navegar a Google Maps
            maps_url = f"https://www.google.com/maps/search/{search_term.replace(' ', '+')}"
            logger.info(f"Navegando a: {maps_url}")
            await page.goto(maps_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            # Aceptar cookies/términos
            try:
                accept_btn = await page.query_selector('button[aria-label*="Aceptar"]')
                if not accept_btn:
                    accept_btn = await page.query_selector('button:has-text("Accept")')
                if accept_btn:
                    await accept_btn.click()
                    logger.debug("Cookies aceptadas")
                    await page.wait_for_timeout(1000)
            except Exception as e:
                logger.debug(f"No se pudo aceptar cookies: {e}")

            # Esperar a que carguen los resultados
            logger.info("Esperando carga de resultados...")
            try:
                await page.wait_for_selector('div[role="feed"]', timeout=10000)
            except PlaywrightTimeout:
                logger.error("Timeout esperando resultados. La búsqueda puede no ser válida.")
                await browser.close()
                return []

            # Scrollear para cargar más resultados
            await scroll_results(page, max_results)

            # Obtener items cargados
            items = await page.query_selector_all('div[role="feed"] > div > div[jsaction]')
            total = min(len(items), max_results)
            logger.info(f"Encontrados {len(items)} negocios. Extrayendo {total}...")

            # Extraer datos de cada item
            for i, item in enumerate(items[:max_results]):
                try:
                    await item.click()
                    await page.wait_for_timeout(1500)

                    # Esperar a que cargue el panel de detalles
                    try:
                        await page.wait_for_selector('h1[class*="DUwDvf"]', timeout=5000)
                    except PlaywrightTimeout:
                        logger.debug(f"Timeout en detalles del item {i+1}")

                    # Extraer datos
                    data = await extract_business_data(page)

                    if data["nombre"]:
                        results.append(data)
                        has_website = "🌐" if data["sitio_web"] else "📵"
                        logger.info(
                            f"[{i+1}/{total}] {has_website} {data['nombre']} "
                            f"— {data['categoria']}"
                        )
                    else:
                        logger.warning(f"[{i+1}/{total}] No se extrajeron datos válidos")

                except Exception as e:
                    logger.error(f"[{i+1}/{total}] Error extrayendo item: {e}", exc_info=False)
                    continue

            await browser.close()
            logger.info("Navegador cerrado")

        except Exception as e:
            logger.error(f"Error fatal durante el scraping: {e}", exc_info=True)
            return []

    # Guardar resultados
    if not results:
        logger.warning("No se extrajeron resultados")
        return []

    try:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Guardando {len(results)} resultados en {output_file}")

        # Importar CSV aquí para evitar dependencias circulares
        import csv

        with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(results)

        con_web = sum(1 for r in results if r["sitio_web"])
        sin_web = len(results) - con_web

        logger.info(
            f"✅ CSV guardado | Total: {len(results)} | "
            f"Con web: {con_web} | Sin web: {sin_web}"
        )

    except Exception as e:
        logger.error(f"Error guardando CSV: {e}", exc_info=True)

    return results
