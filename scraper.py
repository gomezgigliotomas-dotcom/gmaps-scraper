"""
Google Maps Business Scraper - Wrapper para compatibilidad hacia atrás.

Este archivo mantiene compatibilidad con versiones anteriores.
El código principal está en la carpeta 'src/' con mejor estructura.
"""

import sys
from pathlib import Path

# Agregar src al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main

if __name__ == "__main__":
    main()
