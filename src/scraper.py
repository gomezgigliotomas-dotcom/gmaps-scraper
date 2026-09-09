"""
Google Maps Business Scraper - Módulo principal de scraping.
Contiene la lógica de navegación y scroll en Google Maps.
"""

import csv
import logging
from typing import List, Dict, Any
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from playwright.async_api import Page

from .extractors import extract_business_data, FIELDNAMES
from .retry import retry_async
from .config import load_config

logger = logging.getLogger(__name__)


async def scroll_results(page: Page, max_results: int, selectors: Dict[str, str], timeouts: Dict[str, int]) -> None:
    """
    Scrollea la lista de resultados para cargar más items.

    Args:
        page: Página de Playwright
        max_results: Máximo número de resultados a cargar
        selectors: Selectores CSS desde config
        timeouts: Timeouts en ms desde config
    """
    feed = await page.query_selector(selectors["results_list"])
    if not feed:
        logger.warning("No se encontró el panel de resultados")
        return

    last_count = 0
    stall_count = 0

    while True:
        items = await page.query_selector_all(selectors["result_item"])
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
        await page.wait_for_timeout(timeouts["scroll_wait_ms"])

        # Verificar si alcanzamos el final
        end_msg = await page.query_selector(selectors["end_of_results"])
        if end_msg:
            logger.info("Se alcanzó el final de los resultados")
            break


async def _extract_item_with_retry(
    page: Page,
    item: Any,
    selectors: Dict[str, str],
    timeouts: Dict[str, int],
    retry_cfg: Dict[str, float],
) -> Dict[str, str]:
    """Click en un item y extrae sus datos, con reintentos ante fallos temporales."""

    async def _attempt() -> Dict[str, str]:
        await item.click()
        await page.wait_for_timeout(timeouts["item_click_wait_ms"])
        try:
            await page.wait_for_selector(
                selectors["business_name"], timeout=timeouts["detail_panel_ms"]
            )
        except PlaywrightTimeout:
            # No es fatal: puede que el negocio no tenga ese selector exacto.
            # extract_business_data devuelve "" para nombre y se descarta arriba.
            pass

        data = await extract_business_data(page, selectors)
        if not data["nombre"]:
            raise RuntimeError("No se pudo extraer el nombre del negocio")
        return data

    return await retry_async(
        _attempt,
        max_attempts=retry_cfg["max_attempts"],
        base_delay=retry_cfg["base_delay_seconds"],
        max_delay=retry_cfg["max_delay_seconds"],
        exponential_base=retry_cfg["exponential_base"],
        operation_name="extracción de item",
    )


async def scrape(
    query: str,
    location: str,
    max_results: int,
    output_file: str,
    headless: bool,
    config_path: str = "",
) -> List[Dict[str, str]]:
    """
    Realiza el scraping de negocios en Google Maps.

    Args:
        query: Término de búsqueda (ej: "dentistas")
        location: Ubicación (ej: "Buenos Aires")
        max_results: Máximo de resultados a extraer
        output_file: Path del archivo CSV de salida
        headless: Si True, ejecuta sin mostrar navegador
        config_path: Path a config JSON alternativo (opcional)

    Returns:
        Lista de diccionarios con datos de negocios
    """
    config = load_config(config_path)
    selectors = config["selectors"]
    timeouts = config["timeouts"]
    retry_cfg = config["retry"]
    defaults = config["defaults"]

    search_term = f"{query} en {location}"
    results: List[Dict[str, str]] = []

    logger.info(f"Iniciando scraping: {search_term}")
    logger.info(f"Máximo de resultados: {max_results}")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                locale=defaults["locale"],
                viewport=defaults["viewport"],
            )
            page = await context.new_page()

            # Navegar a Google Maps
            maps_url = f"https://www.google.com/maps/search/{search_term.replace(' ', '+')}"
            logger.info(f"Navegando a: {maps_url}")
            await page.goto(maps_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(timeouts["page_load_ms"])

            # Aceptar cookies/términos
            try:
                accept_btn = await page.query_selector(selectors["cookie_accept_aria"])
                if not accept_btn:
                    accept_btn = await page.query_selector(selectors["cookie_accept_text"])
                if accept_btn:
                    await accept_btn.click()
                    logger.debug("Cookies aceptadas")
                    await page.wait_for_timeout(timeouts["cookie_accept_ms"])
            except Exception as e:
                logger.debug(f"No se pudo aceptar cookies: {e}")

            # Esperar a que carguen los resultados
            logger.info("Esperando carga de resultados...")
            try:
                await page.wait_for_selector(
                    selectors["results_list"], timeout=timeouts["results_panel_ms"]
                )
            except PlaywrightTimeout:
                logger.error("Timeout esperando resultados. La búsqueda puede no ser válida.")
                await browser.close()
                return []

            # Scrollear para cargar más resultados
            await scroll_results(page, max_results, selectors, timeouts)

            # Obtener items cargados
            items = await page.query_selector_all(selectors["result_item"])
            total = min(len(items), max_results)
            logger.info(f"Encontrados {len(items)} negocios. Extrayendo {total}...")

            # Extraer datos de cada item (con retry ante fallos temporales)
            for i, item in enumerate(items[:max_results]):
                try:
                    data = await _extract_item_with_retry(
                        page, item, selectors, timeouts, retry_cfg
                    )
                    results.append(data)
                    has_website = "🌐" if data["sitio_web"] else "📵"
                    logger.info(
                        f"[{i+1}/{total}] {has_website} {data['nombre']} "
                        f"— {data['categoria']}"
                    )
                except Exception as e:
                    logger.error(
                        f"[{i+1}/{total}] Descartado tras reintentos: {e}",
                        exc_info=False,
                    )
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
