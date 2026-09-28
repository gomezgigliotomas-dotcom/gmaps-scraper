"""
Configuración de logging profesional para el scraper.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Nombre del paquete ("src"). Todos los módulos internos usan
# logging.getLogger(__name__), que resuelve a "src.scraper", "src.retry",
# etc. — al configurar el logger con ESTE nombre como raíz, esos loggers
# heredan sus handlers automáticamente por la jerarquía de logging de
# Python (en vez de caer al root logger, sin handlers, y perderse).
PACKAGE_LOGGER_NAME = __package__ or "src"


def setup_logger(
    name: str,
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Configura un logger profesional con handlers a consola y opcionalmente a archivo.

    Args:
        name: Nombre del logger
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path opcional para guardar logs en archivo

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Evitar duplicar handlers si ya existen
    if logger.handlers:
        return logger

    # Formato consistente con timestamp
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler a consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler a archivo si se especifica
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
