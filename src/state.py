"""
Persistencia de estado para poder reanudar un scraping interrumpido
(por un error, un Ctrl+C, o un bloqueo de Google Maps a mitad de corrida).

El estado de cada búsqueda (query + location + max_results) se identifica
por un hash y se guarda incrementalmente en .gmaps_state/<hash>.json.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_STATE_DIR = Path(".gmaps_state")


def _run_id(query: str, location: str, max_results: int) -> str:
    """Genera un identificador estable para una combinación de búsqueda."""
    raw = f"{query.lower()}|{location.lower()}|{max_results}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get_state_path(
    query: str,
    location: str,
    max_results: int,
    state_dir: Path = DEFAULT_STATE_DIR,
) -> Path:
    """Retorna el path del archivo de estado para esta búsqueda."""
    return state_dir / f"{_run_id(query, location, max_results)}.json"


def load_state(state_path: Path) -> Optional[Dict[str, Any]]:
    """
    Carga el estado guardado, si existe.

    Returns:
        Dict con el estado, o None si no hay estado previo o está corrupto
    """
    if not state_path.exists():
        return None

    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        logger.info(
            f"📂 Estado previo encontrado: {len(state.get('results', []))} "
            f"resultados ya extraídos ({state_path.name})"
        )
        return state
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"No se pudo leer el estado previo ({state_path}): {e}")
        return None


def save_state(
    state_path: Path,
    query: str,
    location: str,
    max_results: int,
    output_file: str,
    results: List[Dict[str, str]],
    processed_count: int,
) -> None:
    """Guarda el estado actual del scraping (llamar incrementalmente)."""
    state_path.parent.mkdir(parents=True, exist_ok=True)

    existing = load_state(state_path) if state_path.exists() else None
    created_at = existing["created_at"] if existing else datetime.now().isoformat()

    state = {
        "query": query,
        "location": location,
        "max_results": max_results,
        "output_file": output_file,
        "processed_count": processed_count,
        "results": results,
        "created_at": created_at,
        "updated_at": datetime.now().isoformat(),
    }

    try:
        # Escritura atómica: escribe a un temp y renombra, para no corromper
        # el estado si el proceso se corta justo durante el write.
        tmp_path = state_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        tmp_path.replace(state_path)
    except OSError as e:
        logger.warning(f"No se pudo guardar el estado ({state_path}): {e}")


def clear_state(state_path: Path) -> None:
    """Elimina el archivo de estado (llamar al completar exitosamente)."""
    try:
        if state_path.exists():
            state_path.unlink()
            logger.debug(f"Estado limpiado: {state_path}")
    except OSError as e:
        logger.warning(f"No se pudo eliminar el estado ({state_path}): {e}")
