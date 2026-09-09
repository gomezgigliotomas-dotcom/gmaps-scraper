"""
Soporte de proxies para evitar bloqueos/CAPTCHAs de Google Maps.

Permite:
- Usar un proxy fijo (--proxy)
- Rotar al azar entre una lista de proxies (--proxy-file), eligiendo uno
  distinto en cada corrida del scraper

Formatos de proxy aceptados:
    host:port
    user:pass@host:port
    http://host:port
    http://user:pass@host:port
    socks5://host:port
    socks5://user:pass@host:port
"""

import random
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_PROXY_LINE_PATTERN = re.compile(
    r"^(?:(?P<scheme>https?|socks5)://)?"
    r"(?:(?P<username>[^:@/]+):(?P<password>[^:@/]+)@)?"
    r"(?P<host>[^:/@]+):(?P<port>\d{1,5})$"
)


class ProxyError(Exception):
    """Error de configuración o parseo de proxy."""


def parse_proxy(proxy_str: str) -> Dict[str, str]:
    """
    Parsea un string de proxy al formato que espera Playwright.

    Args:
        proxy_str: proxy en cualquiera de los formatos soportados

    Returns:
        Dict compatible con el parámetro `proxy` de
        `chromium.launch()`: {"server": "..."} y opcionalmente
        "username"/"password"

    Raises:
        ProxyError: si el formato no es reconocible
    """
    proxy_str = proxy_str.strip()
    if not proxy_str:
        raise ProxyError("Proxy vacío")

    match = _PROXY_LINE_PATTERN.match(proxy_str)
    if not match:
        raise ProxyError(
            f"Formato de proxy inválido: {mask_credentials(proxy_str)!r}. "
            "Formatos aceptados: host:port, user:pass@host:port, "
            "http://host:port, socks5://host:port"
        )

    scheme = match.group("scheme") or "http"
    host = match.group("host")
    port = int(match.group("port"))
    username = match.group("username")
    password = match.group("password")

    if not (1 <= port <= 65535):
        raise ProxyError(f"Puerto de proxy inválido: {port}")

    result: Dict[str, str] = {"server": f"{scheme}://{host}:{port}"}
    if username and password:
        result["username"] = username
        result["password"] = password

    return result


def load_proxy_list(file_path: str) -> List[str]:
    """
    Carga una lista de proxies desde un archivo de texto (uno por línea).
    Ignora líneas vacías y comentarios (que empiezan con '#').

    Args:
        file_path: path al archivo de proxies

    Returns:
        Lista de strings de proxy (sin parsear)

    Raises:
        ProxyError: si el archivo no existe o está vacío
    """
    path = Path(file_path)
    if not path.exists():
        raise ProxyError(f"Archivo de proxies no encontrado: {file_path}")

    proxies = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            proxies.append(line)

    if not proxies:
        raise ProxyError(f"El archivo de proxies está vacío: {file_path}")

    return proxies


def select_proxy(
    proxy: Optional[str] = None,
    proxy_file: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """
    Selecciona el proxy a usar para esta corrida del scraper.

    Args:
        proxy: un proxy individual (mutuamente excluyente con proxy_file)
        proxy_file: path a un archivo con lista de proxies; se elige
                    uno al azar

    Returns:
        Dict en formato Playwright, o None si no se configuró ningún proxy

    Raises:
        ProxyError: si se pasan ambos parámetros, o si hay un problema
                    parseando/cargando el proxy
    """
    if proxy and proxy_file:
        raise ProxyError(
            "No se puede especificar --proxy y --proxy-file al mismo tiempo"
        )

    if proxy:
        selected = proxy
        logger.info(f"🌐 Usando proxy fijo: {mask_credentials(selected)}")
    elif proxy_file:
        proxies = load_proxy_list(proxy_file)
        selected = random.choice(proxies)
        logger.info(
            f"🌐 Proxy elegido al azar de {len(proxies)} disponibles: "
            f"{mask_credentials(selected)}"
        )
    else:
        logger.debug("Sin proxy configurado (conexión directa)")
        return None

    return parse_proxy(selected)


def mask_credentials(proxy_str: str) -> str:
    """Oculta usuario/contraseña en un string de proxy, para logging seguro."""
    # Cubre tanto "scheme://user:pass@host" como "user:pass@host" (sin scheme)
    return re.sub(r"(^|://)[^:@/]+:[^:@/]+@", r"\1***:***@", proxy_str)
