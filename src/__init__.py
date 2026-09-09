"""
Google Maps Business Scraper
Módulo para extraer leads de Google Maps para agencias de Google Ads.
"""

__version__ = "2.0.0"
__author__ = "Tomás Goez Giglio"
__description__ = "Scraper profesional de Google Maps con logging, modulación y type hints"

from .scraper import scrape
from .logger import setup_logger

__all__ = ["scrape", "setup_logger"]
