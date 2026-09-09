"""Tests de validación de inputs del CLI (src/main.py)."""

import logging
import pytest

from src.main import (
    validate_query,
    validate_location,
    validate_max_results,
    validate_output_path,
    validate_config_path,
    generate_output_filename,
)


class TestValidateQuery:
    def test_query_valida_se_devuelve_limpia(self):
        assert validate_query("  dentistas  ") == "dentistas"

    def test_query_vacia_lanza_error(self):
        with pytest.raises(ValueError, match="no puede estar vacía"):
            validate_query("")

    def test_query_solo_espacios_lanza_error(self):
        with pytest.raises(ValueError, match="no puede estar vacía"):
            validate_query("   ")

    def test_query_demasiado_larga_lanza_error(self):
        with pytest.raises(ValueError, match="demasiado largo"):
            validate_query("a" * 201)

    def test_query_con_caracteres_invalidos_lanza_error(self):
        with pytest.raises(ValueError, match="caracteres inválidos"):
            validate_query("dentistas/../etc")

    def test_query_con_caracter_de_control_lanza_error(self):
        with pytest.raises(ValueError, match="caracteres inválidos"):
            validate_query("dentistas\x00malicioso")


class TestValidateLocation:
    def test_location_valida_se_devuelve_limpia(self):
        assert validate_location("  Buenos Aires  ") == "Buenos Aires"

    def test_location_vacia_lanza_error(self):
        with pytest.raises(ValueError, match="no puede estar vacía"):
            validate_location("")

    def test_location_con_barra_lanza_error(self):
        with pytest.raises(ValueError, match="caracteres inválidos"):
            validate_location("Buenos Aires\\Palermo")


class TestValidateMaxResults:
    def test_max_valido_no_lanza(self):
        logger = logging.getLogger("test")
        validate_max_results(50, logger)  # no debe lanzar

    def test_max_cero_lanza_error(self):
        logger = logging.getLogger("test")
        with pytest.raises(ValueError, match="mayor a 0"):
            validate_max_results(0, logger)

    def test_max_negativo_lanza_error(self):
        logger = logging.getLogger("test")
        with pytest.raises(ValueError, match="mayor a 0"):
            validate_max_results(-5, logger)

    def test_max_alto_solo_loguea_warning(self, caplog):
        logger = logging.getLogger("test")
        with caplog.at_level(logging.WARNING):
            validate_max_results(200, logger, hard_max=120)
        assert "limita" in caplog.text.lower()


class TestValidateOutputPath:
    def test_output_vacio_se_permite(self):
        assert validate_output_path("") == ""

    def test_output_csv_valido(self):
        assert validate_output_path("leads.csv") == "leads.csv"

    def test_output_sin_extension_csv_lanza_error(self):
        with pytest.raises(ValueError, match="debe terminar en .csv"):
            validate_output_path("leads.txt")


class TestValidateConfigPath:
    def test_config_vacio_se_permite(self):
        assert validate_config_path("") == ""

    def test_config_inexistente_lanza_error(self):
        with pytest.raises(ValueError, match="no encontrado"):
            validate_config_path("/ruta/que/no/existe.json")


class TestGenerateOutputFilename:
    def test_genera_nombre_con_query_y_location(self):
        filename = generate_output_filename("dentistas", "Buenos Aires")
        assert filename.startswith("resultados_dentistas_buenos_aires_")
        assert filename.endswith(".csv")

    def test_sanitiza_caracteres_especiales(self):
        filename = generate_output_filename("café & té", "Palermo, CABA")
        assert "/" not in filename
        assert "&" not in filename
