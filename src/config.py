"""
Carga y validación de configuración desde JSON.
Permite ajustar selectores, timeouts y valores default sin tocar código.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.json"

REQUIRED_TOP_LEVEL_KEYS = {"selectors", "timeouts", "retry", "defaults"}
REQUIRED_SELECTOR_KEYS = {
    "results_list",
    "result_item",
    "business_name",
    "rating",
    "reviews_count",
    "category",
    "address",
    "phone",
    "website",
    "open_status",
}


class ConfigError(Exception):
    """Error de configuración inválida o faltante."""


def load_config(config_path: str = "") -> Dict[str, Any]:
    """
    Carga la configuración desde un archivo JSON.

    Args:
        config_path: Path al archivo de config. Si está vacío, usa el default.

    Returns:
        Diccionario con la configuración cargada

    Raises:
        ConfigError: si el archivo no existe, tiene JSON inválido,
                     o le faltan claves requeridas
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if not path.exists():
        raise ConfigError(f"Archivo de configuración no encontrado: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"JSON inválido en {path}: {e}") from e

    _validate_config(config, path)
    logger.debug(f"Configuración cargada desde {path}")
    return config


def _validate_config(config: Dict[str, Any], path: Path) -> None:
    """Valida que la config tenga la estructura mínima esperada."""
    missing_top = REQUIRED_TOP_LEVEL_KEYS - config.keys()
    if missing_top:
        raise ConfigError(
            f"Config {path} le faltan claves requeridas: {missing_top}"
        )

    missing_selectors = REQUIRED_SELECTOR_KEYS - config["selectors"].keys()
    if missing_selectors:
        raise ConfigError(
            f"Config {path} le faltan selectores requeridos: {missing_selectors}"
        )

    retry = config["retry"]
    if retry.get("max_attempts", 0) < 1:
        raise ConfigError("retry.max_attempts debe ser >= 1")
