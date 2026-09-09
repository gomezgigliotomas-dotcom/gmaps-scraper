"""Tests para extracción de datos (src/extractors.py) usando mocks de Playwright."""

from typing import Optional
from unittest.mock import AsyncMock
import pytest

from src.extractors import extract_business_data, FIELDNAMES
from src.config import load_config


@pytest.fixture
def selectors():
    return load_config()["selectors"]


def make_element(text: str = "", attrs: Optional[dict] = None):
    """Crea un mock de ElementHandle de Playwright."""
    el = AsyncMock()
    el.inner_text.return_value = text
    attrs = attrs or {}
    el.get_attribute.side_effect = lambda name: attrs.get(name)
    return el


class TestExtractBusinessData:
    @pytest.mark.asyncio
    async def test_extrae_todos_los_campos_cuando_estan_presentes(self, selectors):
        page = AsyncMock()

        elements_by_selector = {
            selectors["business_name"]: make_element("Dentista Pérez"),
            selectors["rating"]: make_element("4.5"),
            selectors["reviews_count"]: make_element(
                attrs={"aria-label": "120 reseñas"}
            ),
            selectors["category"]: make_element("Dentista"),
            selectors["address"]: make_element("Av. Siempre Viva 123"),
            selectors["phone"]: make_element("11-1234-5678"),
            selectors["website"]: make_element(attrs={"href": "https://dentista.com"}),
            selectors["open_status"]: make_element("Abierto"),
        }

        page.query_selector.side_effect = lambda sel: elements_by_selector.get(sel)

        data = await extract_business_data(page, selectors)

        assert data["nombre"] == "Dentista Pérez"
        assert data["rating"] == "4.5"
        assert data["cantidad_reviews"] == "120"
        assert data["categoria"] == "Dentista"
        assert data["direccion"] == "Av. Siempre Viva 123"
        assert data["telefono"] == "11-1234-5678"
        assert data["sitio_web"] == "https://dentista.com"
        assert data["horario_estado"] == "Abierto"

    @pytest.mark.asyncio
    async def test_campos_ausentes_quedan_vacios(self, selectors):
        page = AsyncMock()
        page.query_selector.return_value = None

        data = await extract_business_data(page, selectors)

        assert set(data.keys()) == set(FIELDNAMES)
        assert all(v == "" for v in data.values())

    @pytest.mark.asyncio
    async def test_negocio_sin_sitio_web(self, selectors):
        page = AsyncMock()

        elements_by_selector = {
            selectors["business_name"]: make_element("Restaurante Sin Web"),
        }
        page.query_selector.side_effect = lambda sel: elements_by_selector.get(sel)

        data = await extract_business_data(page, selectors)

        assert data["nombre"] == "Restaurante Sin Web"
        assert data["sitio_web"] == ""

    @pytest.mark.asyncio
    async def test_reviews_con_formato_de_miles(self, selectors):
        page = AsyncMock()
        elements_by_selector = {
            selectors["business_name"]: make_element("Negocio Popular"),
            selectors["reviews_count"]: make_element(
                attrs={"aria-label": "1.234 reseñas"}
            ),
        }
        page.query_selector.side_effect = lambda sel: elements_by_selector.get(sel)

        data = await extract_business_data(page, selectors)

        assert data["cantidad_reviews"] == "1.234"

    @pytest.mark.asyncio
    async def test_excepcion_en_un_campo_no_rompe_extraccion_completa(self, selectors):
        page = AsyncMock()

        broken_el = AsyncMock()
        broken_el.inner_text.side_effect = Exception("elemento desapareció del DOM")

        elements_by_selector = {
            selectors["business_name"]: make_element("Negocio Resiliente"),
            selectors["rating"]: broken_el,
        }
        page.query_selector.side_effect = lambda sel: elements_by_selector.get(sel)

        data = await extract_business_data(page, selectors)

        assert data["nombre"] == "Negocio Resiliente"
        assert data["rating"] == ""
