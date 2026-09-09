"""Tests para utilidades de src/scraper.py (sin levantar un browser real)."""

from src.scraper import _dedup_key


class TestDedupKey:
    """
    Regresión: Google Maps no garantiza el mismo orden de resultados entre
    cargas de página distintas. Al retomar con --resume, el negocio que
    cae en la posición N puede no ser el mismo que se guardó ahí la vez
    anterior, produciendo duplicados en el CSV final si no se deduplica.
    """

    def test_mismo_nombre_y_direccion_da_misma_clave(self):
        a = {"nombre": "Dental Palermo", "direccion": "Charcas 3127, CABA"}
        b = {"nombre": "Dental Palermo", "direccion": "Charcas 3127, CABA"}
        assert _dedup_key(a) == _dedup_key(b)

    def test_es_insensible_a_mayusculas_y_espacios(self):
        a = {"nombre": "Dental Palermo", "direccion": "Charcas 3127, CABA"}
        b = {"nombre": "  dental palermo  ", "direccion": "  charcas 3127, caba  "}
        assert _dedup_key(a) == _dedup_key(b)

    def test_mismo_nombre_distinta_direccion_da_distinta_clave(self):
        """Cadenas con sucursales (mismo nombre, distinta dirección) no
        deben tratarse como duplicados."""
        a = {"nombre": "Farmacity", "direccion": "Av. Santa Fe 1000"}
        b = {"nombre": "Farmacity", "direccion": "Av. Cabildo 2000"}
        assert _dedup_key(a) != _dedup_key(b)

    def test_campos_faltantes_no_lanzan_error(self):
        assert _dedup_key({}) == ("", "")
