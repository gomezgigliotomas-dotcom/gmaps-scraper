"""Tests para carga y validación de configuración (src/config.py)."""

import json
import pytest

from src.config import load_config, ConfigError, DEFAULT_CONFIG_PATH


class TestLoadConfig:
    def test_carga_config_default(self):
        config = load_config()
        assert "selectors" in config
        assert "timeouts" in config
        assert "retry" in config
        assert "defaults" in config

    def test_config_default_existe_en_disco(self):
        assert DEFAULT_CONFIG_PATH.exists()

    def test_archivo_inexistente_lanza_error(self):
        with pytest.raises(ConfigError, match="no encontrado"):
            load_config("/ruta/inexistente/config.json")

    def test_json_invalido_lanza_error(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{ esto no es json valido ]")
        with pytest.raises(ConfigError, match="JSON inválido"):
            load_config(str(bad_file))

    def test_config_sin_claves_requeridas_lanza_error(self, tmp_path):
        incomplete = tmp_path / "incomplete.json"
        incomplete.write_text(json.dumps({"selectors": {}}))
        with pytest.raises(ConfigError, match="faltan claves requeridas"):
            load_config(str(incomplete))

    def test_config_sin_selectores_requeridos_lanza_error(self, tmp_path):
        missing_selectors = tmp_path / "missing_sel.json"
        missing_selectors.write_text(json.dumps({
            "selectors": {"results_list": "div"},
            "timeouts": {},
            "retry": {"max_attempts": 3},
            "defaults": {},
        }))
        with pytest.raises(ConfigError, match="faltan selectores requeridos"):
            load_config(str(missing_selectors))

    def test_retry_max_attempts_invalido_lanza_error(self, tmp_path):
        base_config = json.loads(DEFAULT_CONFIG_PATH.read_text())
        base_config["retry"]["max_attempts"] = 0
        bad_retry = tmp_path / "bad_retry.json"
        bad_retry.write_text(json.dumps(base_config))
        with pytest.raises(ConfigError, match="max_attempts debe ser"):
            load_config(str(bad_retry))
