"""
Soporte para correr múltiples búsquedas (query + location) en una sola
invocación, leyendo la lista desde un archivo CSV.

Formato esperado del CSV (con encabezado):
    query,location,max
    dentistas,Buenos Aires,50
    restaurantes,"Palermo, Buenos Aires",100
    abogados,Córdoba,

La columna "max" es opcional por fila; si está vacía, se usa el --max
global pasado por CLI.
"""

import csv
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"query", "location"}


class BatchError(Exception):
    """Error leyendo o procesando el archivo de batch."""


def load_batch_file(file_path: str, default_max: int) -> List[Dict[str, Any]]:
    """
    Carga las búsquedas a ejecutar desde un archivo CSV.

    Args:
        file_path: path al CSV con columnas query,location[,max]
        default_max: valor de `max` a usar si la fila no lo especifica

    Returns:
        Lista de dicts: [{"query": ..., "location": ..., "max": int}, ...]

    Raises:
        BatchError: si el archivo no existe, está vacío, o le faltan
                    columnas requeridas
    """
    path = Path(file_path)
    if not path.exists():
        raise BatchError(f"Archivo de batch no encontrado: {file_path}")

    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise BatchError(f"El archivo de batch está vacío: {file_path}")

        missing = REQUIRED_COLUMNS - {c.strip().lower() for c in reader.fieldnames}
        if missing:
            raise BatchError(
                f"Al archivo de batch le faltan columnas requeridas: {missing} "
                f"(columnas encontradas: {reader.fieldnames})"
            )

        searches: List[Dict[str, Any]] = []
        for row_num, row in enumerate(reader, start=2):  # fila 1 = encabezado
            row = {k.strip().lower(): (v or "").strip() for k, v in row.items()}

            query = row.get("query", "")
            location = row.get("location", "")
            if not query or not location:
                logger.warning(
                    f"Fila {row_num} del batch ignorada: query/location vacíos"
                )
                continue

            max_str = row.get("max", "")
            try:
                max_results = int(max_str) if max_str else default_max
            except ValueError:
                logger.warning(
                    f"Fila {row_num}: 'max' inválido ({max_str!r}), "
                    f"usando default {default_max}"
                )
                max_results = default_max

            searches.append({"query": query, "location": location, "max": max_results})

    if not searches:
        raise BatchError(f"No se encontraron búsquedas válidas en: {file_path}")

    logger.info(f"📋 Batch cargado: {len(searches)} búsquedas desde {file_path}")
    return searches


def generate_batch_output_filename(query: str, location: str) -> str:
    """Genera el nombre de CSV individual para una búsqueda del batch."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_query = re.sub(r"[^\w]", "_", query.lower())
    safe_location = re.sub(r"[^\w]", "_", location.lower())
    return f"resultados_{safe_query}_{safe_location}_{timestamp}.csv"


def combine_csv_files(csv_paths: List[str], combined_output: str, fieldnames: List[str]) -> int:
    """
    Combina varios CSVs (mismo esquema de columnas) en un único archivo.

    Args:
        csv_paths: paths a los CSVs individuales a combinar
        combined_output: path del CSV combinado de salida
        fieldnames: columnas esperadas (deben coincidir con las de cada CSV)

    Returns:
        Cantidad total de filas combinadas
    """
    total_rows = 0
    Path(combined_output).parent.mkdir(parents=True, exist_ok=True)

    with open(combined_output, "w", newline="", encoding="utf-8-sig") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        writer.writeheader()

        for csv_path in csv_paths:
            if not Path(csv_path).exists():
                logger.warning(f"CSV esperado no encontrado, se omite: {csv_path}")
                continue
            with open(csv_path, "r", encoding="utf-8-sig") as in_f:
                reader = csv.DictReader(in_f)
                for row in reader:
                    writer.writerow(row)
                    total_rows += 1

    logger.info(f"📎 Combinado {len(csv_paths)} archivos → {combined_output} ({total_rows} filas)")
    return total_rows
