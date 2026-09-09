"""
Retry logic con exponential backoff para operaciones asíncronas
propensas a fallos temporales (timeouts, elementos no cargados aún).
"""

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_async(
    func: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
    exponential_base: float = 2.0,
    operation_name: str = "operación",
) -> T:
    """
    Ejecuta una función async con reintentos y backoff exponencial.

    Args:
        func: Función async sin argumentos a ejecutar (usar lambda/closure
              para pasar argumentos)
        max_attempts: Número máximo de intentos (>= 1)
        base_delay: Espera inicial en segundos antes del primer reintento
        max_delay: Tope máximo de espera entre reintentos
        exponential_base: Base del crecimiento exponencial (delay = base * exp^n)
        operation_name: Nombre descriptivo para logging

    Returns:
        El resultado de func() si tiene éxito

    Raises:
        La última excepción capturada si se agotan los intentos
    """
    if max_attempts < 1:
        raise ValueError("max_attempts debe ser >= 1")

    last_exception: Exception = RuntimeError(f"{operation_name} nunca se ejecutó")

    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e

            if attempt >= max_attempts:
                logger.error(
                    f"❌ {operation_name} falló tras {max_attempts} intentos: {e}"
                )
                raise

            delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
            logger.warning(
                f"⚠️  {operation_name} falló (intento {attempt}/{max_attempts}): {e}. "
                f"Reintentando en {delay:.1f}s..."
            )
            await asyncio.sleep(delay)

    # Inalcanzable en la práctica (el loop siempre retorna o lanza),
    # pero satisface a los type checkers.
    raise last_exception
