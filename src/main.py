"""
Google Maps Business Scraper - Entrypoint CLI
"""

import asyncio
import argparse
import re
import os
import logging
from datetime import datetime
from pathlib import Path

from .scraper import scrape
from .logger import setup_logger
from .config import ConfigError
from .proxy import select_proxy, ProxyError

# Caracteres de control y separadores de path que no deben aparecer en query/location
_INVALID_CHARS_PATTERN = re.compile(r"[\x00-\x1f\x7f/\\]")
_MAX_INPUT_LENGTH = 200


def validate_query(query: str) -> str:
    """Valida y limpia el término de búsqueda."""
    query = query.strip()
    if not query:
        raise ValueError("La búsqueda (--query) no puede estar vacía")
    if len(query) > _MAX_INPUT_LENGTH:
        raise ValueError(f"--query es demasiado largo (máx {_MAX_INPUT_LENGTH} caracteres)")
    if _INVALID_CHARS_PATTERN.search(query):
        raise ValueError("--query contiene caracteres inválidos (control chars, / o \\)")
    return query


def validate_location(location: str) -> str:
    """Valida y limpia la ubicación."""
    location = location.strip()
    if not location:
        raise ValueError("La ubicación (--location) no puede estar vacía")
    if len(location) > _MAX_INPUT_LENGTH:
        raise ValueError(f"--location es demasiado largo (máx {_MAX_INPUT_LENGTH} caracteres)")
    if _INVALID_CHARS_PATTERN.search(location):
        raise ValueError("--location contiene caracteres inválidos (control chars, / o \\)")
    return location


def validate_max_results(max_results: int, logger: logging.Logger, hard_max: int = 120) -> None:
    """Valida el límite de resultados solicitado."""
    if max_results < 1:
        raise ValueError("--max debe ser mayor a 0")
    if max_results > hard_max:
        logger.warning(
            f"⚠️  Google Maps limita ~{hard_max} resultados por búsqueda. "
            f"Pediste {max_results}; es posible que no se alcancen todos. "
            "Para más cobertura, ejecutá múltiples búsquedas con términos distintos."
        )


def validate_output_path(output: str) -> str:
    """Valida que el path de salida sea un .csv en un directorio escribible."""
    if not output:
        return output

    path = Path(output)

    if path.suffix.lower() != ".csv":
        raise ValueError(f"--output debe terminar en .csv (recibido: {output})")

    parent = path.parent if str(path.parent) != "" else Path(".")
    if parent.exists() and not os.access(parent, os.W_OK):
        raise ValueError(f"No hay permisos de escritura en el directorio: {parent}")

    return output


def validate_config_path(config_path: str) -> str:
    """Valida que el archivo de config exista, si se especificó uno custom."""
    if not config_path:
        return config_path
    if not Path(config_path).exists():
        raise ValueError(f"Archivo de configuración no encontrado: {config_path}")
    return config_path


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
    parser.add_argument(
        "--config",
        default="",
        help="Path a config JSON alternativo (default: config/default.json)",
    )
    parser.add_argument(
        "--proxy",
        default="",
        help=(
            "Proxy fijo para evitar bloqueos de IP "
            '(ej: "http://user:pass@host:port" o "host:port"). '
            "Mutuamente excluyente con --proxy-file."
        ),
    )
    parser.add_argument(
        "--proxy-file",
        default="",
        help=(
            "Archivo con lista de proxies (uno por línea); se elige uno "
            "al azar en cada corrida. Mutuamente excluyente con --proxy."
        ),
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
        validate_max_results(args.max, logger)
        output = validate_output_path(args.output)
        config_path = validate_config_path(args.config)
        proxy = select_proxy(
            proxy=args.proxy or None,
            proxy_file=args.proxy_file or None,
        )

        # Generar nombre de archivo si no se especifica
        output_file = output or generate_output_filename(query, location)

        logger.info(f"📝 Búsqueda: {query}")
        logger.info(f"📍 Ubicación: {location}")
        logger.info(f"📊 Máximo de resultados: {args.max}")
        logger.info(f"💾 Archivo de salida: {output_file}")
        if not proxy:
            logger.info("🌐 Sin proxy — conexión directa (mayor riesgo de bloqueo/CAPTCHA)")

        # Ejecutar scraping
        headless = not args.show_browser
        results = asyncio.run(
            scrape(
                query=query,
                location=location,
                max_results=args.max,
                output_file=output_file,
                headless=headless,
                config_path=config_path,
                proxy=proxy,
            )
        )

        if results:
            logger.info("=" * 60)
            logger.info(f"✅ Scraping completado: {len(results)} negocios extraídos")
            logger.info("=" * 60)
        else:
            logger.warning("⚠️  No se extrajeron resultados")

    except (ValueError, ConfigError, ProxyError) as e:
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
