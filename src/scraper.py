"""
Google Maps Business Scraper - Módulo principal de scraping.
Contiene la lógica de navegación y scroll en Google Maps.
"""

import csv
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from playwright.async_api import Page

from .extractors import extract_business_data, FIELDNAMES
from .retry import retry_async
from .config import load_config
from .state import get_state_path, load_state, save_state, clear_state

logger = logging.getLogger(__name__)


def _dedup_key(data: Dict[str, str]) -> tuple:
    """Clave de deduplicación: nombre + dirección, normalizados."""
    return (data.get("nombre", "").strip().lower(), data.get("direccion", "").strip().lower())


async def _try_extract_single_result(
    page: Page, selectors: Dict[str, str], timeouts: Dict[str, int]
) -> Optional[Dict[str, str]]:
    """
    Cuando muy pocos negocios matchean la búsqueda (a veces uno solo),
    Google Maps no muestra la lista con feed — redirige directo al panel
    de detalle de ese único resultado. div[role="feed"] nunca aparece, así
    que scrape() normalmente reportaría timeout sin extraer nada.

    Se detecta comprobando si el nombre del negocio (h1) está presente:
    si es así, el detalle ya está abierto y se puede extraer directo, sin
    necesidad de scroll ni click.

    Returns:
        Los datos del negocio si se detectó este caso, None si no
        (búsqueda realmente sin resultados o timeout genuino).
    """
    try:
        await page.wait_for_selector(
            selectors["business_name"], timeout=timeouts["detail_panel_ms"]
        )
    except PlaywrightTimeout:
        return None

    data = await extract_business_data(page, selectors)
    return data if data["nombre"] else None


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
        # El primer resultado del feed suele quedar tapado por la barra de
        # filtros de Google Maps (Horario, Rating, etc.) y Playwright lo
        # considera "no visible" para el click hasta que se lo trae a la
        # vista explícitamente.
        await item.scroll_into_view_if_needed()
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
    proxy: Optional[Dict[str, str]] = None,
    resume: bool = False,
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
        proxy: Dict en formato Playwright ({"server": ..., "username": ...,
               "password": ...}) para rutear el tráfico a través de un
               proxy y evitar bloqueos por IP. Ver src/proxy.py.
        resume: Si True, retoma un scraping previo interrumpido para la
                misma query/location/max_results (ver src/state.py)

    Returns:
        Lista de diccionarios con datos de negocios
    """
    config = load_config(config_path)
    selectors = config["selectors"]
    timeouts = config["timeouts"]
    retry_cfg = config["retry"]
    defaults = config["defaults"]

    search_term = f"{query} en {location}"

    state_path = get_state_path(query, location, max_results)
    previous_state = load_state(state_path) if resume else None

    results: List[Dict[str, str]] = list(previous_state["results"]) if previous_state else []
    already_processed = previous_state["processed_count"] if previous_state else 0

    # Google Maps no garantiza el mismo orden de resultados entre cargas de
    # página distintas — al retomar con --resume, el negocio que ahora cae
    # en la posición N puede no ser el mismo que se guardó ahí la vez
    # anterior. Se deduplica por (nombre, dirección) para no repetirlo.
    seen_keys = {_dedup_key(r) for r in results}

    logger.info(f"Iniciando scraping: {search_term}")
    logger.info(f"Máximo de resultados: {max_results}")
    if already_processed:
        logger.info(
            f"▶️  Retomando desde el item {already_processed + 1} "
            f"({len(results)} resultados ya guardados)"
        )

    async with async_playwright() as p:
        try:
            launch_kwargs: Dict[str, Any] = {"headless": headless}
            if proxy:
                launch_kwargs["proxy"] = proxy
                logger.info("🌐 Navegador lanzado a través de proxy")

            browser = await p.chromium.launch(**launch_kwargs)
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
            has_result_list = True
            try:
                await page.wait_for_selector(
                    selectors["results_list"], timeout=timeouts["results_panel_ms"]
                )
            except PlaywrightTimeout:
                has_result_list = False

            if not has_result_list:
                # Cuando muy pocos negocios matchean la búsqueda (a veces
                # uno solo), Google Maps no muestra la lista con feed —
                # redirige directo al panel de detalle de ese resultado
                # único. Se detecta y extrae igual en vez de reportar error.
                single_result = await _try_extract_single_result(page, selectors, timeouts)
                if single_result and not already_processed:
                    key = _dedup_key(single_result)
                    if key not in seen_keys:
                        results.append(single_result)
                        logger.info(
                            f"📍 Un solo negocio coincide con la búsqueda (Google Maps "
                            f"lo abrió directo, sin lista): {single_result['nombre']} "
                            f"— {single_result['categoria']}"
                        )
                elif not single_result:
                    logger.error(
                        "Timeout esperando resultados. La búsqueda puede no ser válida."
                    )
            else:
                # Scrollear para cargar más resultados
                await scroll_results(page, max_results, selectors, timeouts)

                # Obtener items cargados
                items = await page.query_selector_all(selectors["result_item"])
                total = min(len(items), max_results)
                logger.info(f"Encontrados {len(items)} negocios. Extrayendo {total}...")

                # Extraer datos de cada item (con retry ante fallos temporales).
                # Si retomamos una corrida previa, saltamos los items ya procesados.
                for i, item in enumerate(items[:max_results]):
                    if i < already_processed:
                        continue
                    try:
                        data = await _extract_item_with_retry(
                            page, item, selectors, timeouts, retry_cfg
                        )
                        key = _dedup_key(data)
                        if key in seen_keys:
                            logger.debug(
                                f"[{i+1}/{total}] Duplicado (ya extraído en una corrida "
                                f"previa de --resume), se omite: {data['nombre']}"
                            )
                        else:
                            seen_keys.add(key)
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
                    finally:
                        # Guardar progreso incremental: si el proceso se corta acá,
                        # --resume puede retomar desde el próximo item.
                        save_state(
                            state_path, query, location, max_results,
                            output_file, results, i + 1,
                        )

            await browser.close()
            logger.info("Navegador cerrado")

        except Exception as e:
            logger.error(f"Error fatal durante el scraping: {e}", exc_info=True)
            return results

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

        # Scraping completado con éxito: el estado intermedio ya no hace falta
        clear_state(state_path)

    except Exception as e:
        logger.error(f"Error guardando CSV: {e}", exc_info=True)

    return results
