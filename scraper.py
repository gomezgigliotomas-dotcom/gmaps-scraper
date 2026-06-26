"""
Google Maps Business Scraper
Busca negocios en Google Maps y exporta los resultados a CSV.

Uso:
    python scraper.py --query "dentistas" --location "Buenos Aires" --max 50
    python scraper.py --query "restaurantes" --location "Palermo, Buenos Aires" --max 100
"""

import asyncio
import csv
import argparse
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


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

FIELDNAMES = ["nombre", "categoria", "rating", "cantidad_reviews",
              "direccion", "telefono", "sitio_web", "horario_estado"]


async def scroll_results(page, max_results: int):
    feed = await page.query_selector(SELECTORS["results_list"])
    if not feed:
        return

    last_count = 0
    stall_count = 0

    while True:
        items = await page.query_selector_all(SELECTORS["result_item"])
        current_count = len(items)

        if current_count >= max_results:
            break

        if current_count == last_count:
            stall_count += 1
            if stall_count >= 3:
                break
        else:
            stall_count = 0

        last_count = current_count
        await feed.evaluate("el => el.scrollBy(0, 1000)")
        await page.wait_for_timeout(800)

        end_msg = await page.query_selector('span[class*="HlvSq"]')
        if end_msg:
            break


async def extract_business_data(page) -> dict:
    data = {k: "" for k in FIELDNAMES}

    try:
        el = await page.query_selector(SELECTORS["business_name"])
        if el:
            data["nombre"] = (await el.inner_text()).strip()
    except Exception:
        pass

    try:
        el = await page.query_selector(SELECTORS["rating"])
        if el:
            data["rating"] = (await el.inner_text()).strip()
    except Exception:
        pass

    try:
        el = await page.query_selector(SELECTORS["reviews_count"])
        if el:
            aria = await el.get_attribute("aria-label") or ""
            numbers = re.findall(r"[\d,\.]+", aria)
            if numbers:
                data["cantidad_reviews"] = numbers[0].replace(",", "")
    except Exception:
        pass

    try:
        el = await page.query_selector(SELECTORS["category"])
        if el:
            data["categoria"] = (await el.inner_text()).strip()
    except Exception:
        pass

    try:
        el = await page.query_selector(SELECTORS["address"])
        if el:
            data["direccion"] = (await el.inner_text()).strip()
    except Exception:
        pass

    try:
        el = await page.query_selector(SELECTORS["phone"])
        if el:
            data["telefono"] = (await el.inner_text()).strip()
    except Exception:
        pass

    try:
        el = await page.query_selector(SELECTORS["website"])
        if el:
            data["sitio_web"] = await el.get_attribute("href") or ""
    except Exception:
        pass

    try:
        el = await page.query_selector(SELECTORS["open_status"])
        if el:
            data["horario_estado"] = (await el.inner_text()).strip()
    except Exception:
        pass

    return data


async def scrape(query: str, location: str, max_results: int, output_file: str, headless: bool):
    search_term = f"{query} en {location}"
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            locale="es-AR",
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        print(f"🔍 Buscando: {search_term}")
        maps_url = f"https://www.google.com/maps/search/{search_term.replace(' ', '+')}"
        await page.goto(maps_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        try:
            accept_btn = await page.query_selector('button[aria-label*="Aceptar"]')
            if not accept_btn:
                accept_btn = await page.query_selector('button:has-text("Accept")')
            if accept_btn:
                await accept_btn.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        print(f"⏳ Cargando resultados (máximo {max_results})...")
        try:
            await page.wait_for_selector(SELECTORS["results_list"], timeout=10000)
        except PlaywrightTimeout:
            print("❌ No se encontró el panel de resultados. Verificá la búsqueda.")
            await browser.close()
            return []

        await scroll_results(page, max_results)

        items = await page.query_selector_all(SELECTORS["result_item"])
        total = min(len(items), max_results)
        print(f"📋 Encontrados {len(items)} negocios. Extrayendo datos de {total}...")

        for i, item in enumerate(items[:max_results]):
            try:
                await item.click()
                await page.wait_for_timeout(1500)
                try:
                    await page.wait_for_selector(SELECTORS["business_name"], timeout=5000)
                except PlaywrightTimeout:
                    pass

                data = await extract_business_data(page)

                if data["nombre"]:
                    results.append(data)
                    icon = "🌐" if data["sitio_web"] else "📵"
                    print(f"  [{i+1}/{total}] {icon} {data['nombre']} — {data['categoria']}")

            except Exception as e:
                print(f"  [{i+1}/{total}] ⚠️  Error en ítem {i+1}: {e}")
                continue

        await browser.close()

    if not results:
        print("⚠️  No se extrajeron resultados.")
        return []

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(results)

    con_web = sum(1 for r in results if r["sitio_web"])
    sin_web = len(results) - con_web

    print(f"\n✅ CSV guardado en: {output_file}")
    print(f"   Total: {len(results)} negocios  |  Con web: {con_web}  |  Sin web: {sin_web}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Google Maps Business Scraper")
    parser.add_argument("--query", "-q", required=True, help='Rubro a buscar (ej: "dentistas")')
    parser.add_argument("--location", "-l", required=True, help='Ubicación (ej: "Palermo, Buenos Aires")')
    parser.add_argument("--max", "-m", type=int, default=50, help="Máximo de resultados (default: 50)")
    parser.add_argument("--output", "-o", default="", help="Archivo de salida CSV")
    parser.add_argument("--show-browser", action="store_true", help="Mostrar el browser durante el scraping")
    args = parser.parse_args()

    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        safe_query = re.sub(r"[^\w]", "_", args.query.lower())
        safe_location = re.sub(r"[^\w]", "_", args.location.lower())
        args.output = f"resultados_{safe_query}_{safe_location}_{timestamp}.csv"

    asyncio.run(scrape(
        query=args.query,
        location=args.location,
        max_results=args.max,
        output_file=args.output,
        headless=not args.show_browser,
    ))


if __name__ == "__main__":
    main()
