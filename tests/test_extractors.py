"""Tests para extracción de datos (src/extractors.py) usando mocks de Playwright."""

from typing import Optional
from unittest.mock import AsyncMock
import pytest

from src.extractors import extract_business_data, FIELDNAMES, _clean_text
from src.config import load_config

# Caracteres reales observados en el HTML de Google Maps, escritos como
# escapes \uXXXX (ASCII-safe en el código fuente) para no depender de
# glifos invisibles: iconos de su fuente propia (Private Use Area) y un
# narrow no-break space que usa en vez de un espacio normal en horarios.
ICON_CHAR = ""  # ícono de teléfono, tal como aparece en inner_text()
ARROW_ICON_CHAR = ""  # ícono de flecha desplegable (horario_estado)
NARROW_NBSP = " "


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

    @pytest.mark.asyncio
    async def test_no_confunde_aria_label_de_estrellas_con_cantidad_reviews(self, selectors):
        """Regresión: Google Maps a veces solo expone un span de "estrellas
        visuales" (aria-label="4.9 estrellas") en el contenedor de rating,
        sin ningún conteo de reseñas real. Antes, el número dentro de ese
        aria-label ("4.9") se tomaba por error como cantidad_reviews,
        duplicando el valor del rating."""
        page = AsyncMock()
        elements_by_selector = {
            selectors["business_name"]: make_element("Dental Palermo"),
            selectors["rating"]: make_element("4.9"),
            selectors["reviews_count"]: make_element(
                attrs={"aria-label": "4.9 estrellas "}
            ),
        }
        page.query_selector.side_effect = lambda sel: elements_by_selector.get(sel)

        data = await extract_business_data(page, selectors)

        assert data["rating"] == "4.9"
        assert data["cantidad_reviews"] == ""

    @pytest.mark.asyncio
    async def test_direccion_prefiere_aria_label_limpio_sobre_inner_text_con_icono(self, selectors):
        """Regresión: el botón de dirección antepone un ícono de fuente
        (Private Use Area) + salto de línea al texto real en inner_text().
        El aria-label ("Dirección: ...") viene limpio y se debe preferir."""
        page = AsyncMock()
        addr_el = make_element(
            text=f"{ICON_CHAR}\nAv. Rivadavia 4704, C1424 Cdad. Autónoma de Buenos Aires",
            attrs={"aria-label": "Dirección: Av. Rivadavia 4704, C1424 Cdad. Autónoma de Buenos Aires "},
        )
        elements_by_selector = {
            selectors["business_name"]: make_element("Negocio X"),
            selectors["address"]: addr_el,
        }
        page.query_selector.side_effect = lambda sel: elements_by_selector.get(sel)

        data = await extract_business_data(page, selectors)

        assert data["direccion"] == "Av. Rivadavia 4704, C1424 Cdad. Autónoma de Buenos Aires"
        assert ICON_CHAR not in data["direccion"]

    @pytest.mark.asyncio
    async def test_telefono_prefiere_aria_label_limpio_sobre_inner_text_con_icono(self, selectors):
        page = AsyncMock()
        phone_el = make_element(
            text=f"{ICON_CHAR}\n011 2262-3233",
            attrs={"aria-label": "Teléfono: 011 2262-3233 "},
        )
        elements_by_selector = {
            selectors["business_name"]: make_element("Negocio X"),
            selectors["phone"]: phone_el,
        }
        page.query_selector.side_effect = lambda sel: elements_by_selector.get(sel)

        data = await extract_business_data(page, selectors)

        assert data["telefono"] == "011 2262-3233"

    @pytest.mark.asyncio
    async def test_direccion_sin_aria_label_cae_a_inner_text_limpio(self, selectors):
        """Si no hay aria-label disponible, se usa inner_text() igual,
        pasado por la misma limpieza (por si trae el mismo tipo de basura)."""
        page = AsyncMock()
        addr_el = make_element(text=f"{ICON_CHAR}\nCalle Falsa 123")
        elements_by_selector = {
            selectors["business_name"]: make_element("Negocio X"),
            selectors["address"]: addr_el,
        }
        page.query_selector.side_effect = lambda sel: elements_by_selector.get(sel)

        data = await extract_business_data(page, selectors)

        assert data["direccion"] == "Calle Falsa 123"

    @pytest.mark.asyncio
    async def test_horario_estado_limpia_icono_de_flecha_al_final(self, selectors):
        page = AsyncMock()
        status_el = make_element(
            text=f"Abierto · Cierra a las 8{NARROW_NBSP}p.m.\n{ARROW_ICON_CHAR}"
        )
        elements_by_selector = {
            selectors["business_name"]: make_element("Negocio X"),
            selectors["open_status"]: status_el,
        }
        page.query_selector.side_effect = lambda sel: elements_by_selector.get(sel)

        data = await extract_business_data(page, selectors)

        assert data["horario_estado"] == "Abierto · Cierra a las 8 p.m."
        assert ARROW_ICON_CHAR not in data["horario_estado"]


class TestCleanText:
    def test_texto_vacio_o_none(self):
        assert _clean_text("") == ""
        assert _clean_text(None) == ""

    def test_remueve_caracteres_private_use_area(self):
        assert _clean_text(f"{ICON_CHAR}texto normal{ARROW_ICON_CHAR}") == "texto normal"

    def test_normaliza_narrow_no_break_space(self):
        assert _clean_text(f"8:30{NARROW_NBSP}p.m.") == "8:30 p.m."

    def test_colapsa_saltos_de_linea_y_espacios_multiples(self):
        assert _clean_text("linea1\n\n  linea2   linea3") == "linea1 linea2 linea3"

    def test_no_toca_acentos_ni_enie(self):
        assert _clean_text("  Dirección: Ñuñoa  ") == "Dirección: Ñuñoa"
