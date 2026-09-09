"""
Google Maps Business Scraper - Entrypoint CLI
"""

import asyncio
import argparse
import re
import logging
from datetime import datetime
from pathlib import Path

from .scraper import scrape
from .logger import setup_logger


def validate_query(query: str) -> str:
    """Valida y limpia el término de búsqueda."""
    if not query or not query.strip():
        raise ValueError("La búsqueda no puede estar vacía")
    return query.strip()


def validate_location(location: str) -> str:
    """Valida y limpia la ubicación."""
    if not location or not location.strip():
        raise ValueError("La ubicación no puede estar vacía")
    return location.strip()


def generate_output_filename(query: str, location: str) -> str:
    """Genera nombre de archivo automáticamente si no se especifica."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_query = re.sub(r"[^\w]", "_", query.lower())
    safe_location = re.sub(r"[^\w]", "_", location.lower())
    return f"resultados_{safe_query}_{safe_location}_{timestamp}.csv"


def main() -> None:
    """Función principal - CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="🔍 Google Maps Business Scraper para agencias de Google Ads",
        epilog="Ejemplo: python -m src.main --query 'dentistas' --location 'Buenos Aires' --max 50",
    )

    parser.add_argument(
        "--query",
        "-q",
        required=True,
        help='Término a buscar (ej: "dentistas", "restaurantes")',
    )
    parser.add_argument(
        "--location",
        "-l",
        required=True,
        help='Ubicación (ej: "Buenos Aires", "Palermo, Buenos Aires")',
    )
    parser.add_argument(
        "--max",
        "-m",
        type=int,
        default=50,
        help="Máximo de resultados (default: 50, máx recomendado: 120)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="",
        help="Archivo de salida CSV (default: auto-generado)",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Mostrar navegador durante el scraping (útil para debugging)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nivel de logging (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        default="",
        help="Guardar logs en archivo (ej: scraper.log)",
    )

    args = parser.parse_args()

    # Configurar logging
    log_level = getattr(logging, args.log_level.upper())
    logger = setup_logger(
        name="gmaps_scraper",
        log_level=log_level,
        log_file=args.log_file if args.log_file else None,
    )

    logger.info("=" * 60)
    logger.info("🚀 Google Maps Business Scraper iniciado")
    logger.info("=" * 60)

    try:
        # Validar inputs
        query = validate_query(args.query)
        location = validate_location(args.location)

        if args.max < 1:
            raise ValueError("--max debe ser mayor a 0")
        if args.max > 120:
            logger.warning(
                "⚠️  Google Maps limita ~120 resultados por búsqueda. "
                "Para más cobertura, ejecuta múltiples búsquedas."
            )

        # Generar nombre de archivo si no se especifica
        output_file = args.output or generate_output_filename(query, location)

        logger.info(f"📝 Búsqueda: {query}")
        logger.info(f"📍 Ubicación: {location}")
        logger.info(f"📊 Máximo de resultados: {args.max}")
        logger.info(f"💾 Archivo de salida: {output_file}")

        # Ejecutar scraping
        headless = not args.show_browser
        results = asyncio.run(
            scrape(
                query=query,
                location=location,
                max_results=args.max,
                output_file=output_file,
                headless=headless,
            )
        )

        if results:
            logger.info("=" * 60)
            logger.info(f"✅ Scraping completado: {len(results)} negocios extraídos")
            logger.info("=" * 60)
        else:
            logger.warning("⚠️  No se extrajeron resultados")

    except ValueError as e:
        logger.error(f"❌ Error de validación: {e}")
        exit(1)
    except KeyboardInterrupt:
        logger.info("⏸️  Scraping cancelado por el usuario")
        exit(0)
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
