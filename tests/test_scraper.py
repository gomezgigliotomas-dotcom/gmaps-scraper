"""Tests para utilidades de src/scraper.py (sin levantar un browser real)."""

from unittest.mock import AsyncMock
import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeout

from src.scraper import _dedup_key, _try_extract_single_result
from src.config import load_config


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


@pytest.fixture
def selectors():
    return load_config()["selectors"]


@pytest.fixture
def timeouts():
    return load_config()["timeouts"]


class TestTryExtractSingleResult:
    """
    Regresión: cuando muy pocos negocios matchean una búsqueda (a veces
    uno solo), Google Maps no muestra la lista con feed — redirige directo
    al panel de detalle de ese único resultado. div[role="feed"] nunca
    aparece, así que el scraper reportaba "timeout esperando resultados"
    y descartaba la búsqueda entera aunque sí había un negocio real.
    """

    @pytest.mark.asyncio
    async def test_extrae_el_negocio_cuando_hay_resultado_unico(self, selectors, timeouts):
        page = AsyncMock()
        page.wait_for_selector = AsyncMock()  # no lanza timeout: h1 presente

        name_el = AsyncMock()
        name_el.inner_text.return_value = "Blu Auto"
        elements_by_selector = {selectors["business_name"]: name_el}
        page.query_selector.side_effect = lambda sel: elements_by_selector.get(sel)

        result = await _try_extract_single_result(page, selectors, timeouts)

        assert result is not None
        assert result["nombre"] == "Blu Auto"

    @pytest.mark.asyncio
    async def test_retorna_none_si_tampoco_hay_h1(self, selectors, timeouts):
        page = AsyncMock()
        page.wait_for_selector = AsyncMock(side_effect=PlaywrightTimeout("timeout"))

        result = await _try_extract_single_result(page, selectors, timeouts)

        assert result is None

    @pytest.mark.asyncio
    async def test_retorna_none_si_h1_esta_pero_sin_nombre_valido(self, selectors, timeouts):
        """Caso borde: el h1 aparece pero extract_business_data no logra
        leer texto (elemento vacío/roto) — no se debe reportar un negocio
        fantasma con nombre vacío."""
        page = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.query_selector.return_value = None  # nada se puede extraer

        result = await _try_extract_single_result(page, selectors, timeouts)

        assert result is None
