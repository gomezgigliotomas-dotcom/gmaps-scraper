"""
Google Maps Business Scraper
Módulo para extraer leads de Google Maps para agencias de Google Ads.
"""

__version__ = "2.1.0"
__author__ = "Tomás Goez Giglio"
__description__ = "Scraper profesional de Google Maps con logging, retry, config y tests"

from .scraper import scrape
from .logger import setup_logger
from .config import load_config, ConfigError

__all__ = ["scrape", "setup_logger", "load_config", "ConfigError"]
