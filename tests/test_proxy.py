"""Tests para el soporte de proxies (src/proxy.py)."""

import pytest

from src.proxy import (
    parse_proxy,
    load_proxy_list,
    select_proxy,
    mask_credentials,
    ProxyError,
)


class TestParseProxy:
    def test_host_port_simple(self):
        result = parse_proxy("45.32.10.20:8080")
        assert result == {"server": "http://45.32.10.20:8080"}

    def test_con_credenciales(self):
        result = parse_proxy("user123:pass456@45.32.10.20:8080")
        assert result == {
            "server": "http://45.32.10.20:8080",
            "username": "user123",
            "password": "pass456",
        }

    def test_con_scheme_http_explicito(self):
        result = parse_proxy("http://45.32.10.20:8080")
        assert result == {"server": "http://45.32.10.20:8080"}

    def test_con_scheme_y_credenciales(self):
        result = parse_proxy("http://user:pass@45.32.10.20:8080")
        assert result == {
            "server": "http://45.32.10.20:8080",
            "username": "user",
            "password": "pass",
        }

    def test_con_scheme_socks5(self):
        result = parse_proxy("socks5://45.32.10.20:1080")
        assert result == {"server": "socks5://45.32.10.20:1080"}

    def test_proxy_vacio_lanza_error(self):
        with pytest.raises(ProxyError, match="vacío"):
            parse_proxy("")

    def test_proxy_solo_espacios_lanza_error(self):
        with pytest.raises(ProxyError, match="vacío"):
            parse_proxy("   ")

    def test_formato_invalido_lanza_error(self):
        with pytest.raises(ProxyError, match="Formato de proxy inválido"):
            parse_proxy("esto-no-es-un-proxy")

    def test_puerto_no_numerico_lanza_error(self):
        with pytest.raises(ProxyError, match="Formato de proxy inválido"):
            parse_proxy("45.32.10.20:puerto")

    def test_puerto_fuera_de_rango_lanza_error(self):
        with pytest.raises(ProxyError, match="Puerto de proxy inválido"):
            parse_proxy("45.32.10.20:99999")

    def test_error_no_expone_password_en_mensaje(self):
        try:
            parse_proxy("user:supersecreto@host-malformado")
        except ProxyError as e:
            assert "supersecreto" not in str(e)
            assert "***:***@" in str(e)


class TestLoadProxyList:
    def test_carga_lista_valida(self, tmp_path):
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text("45.32.10.20:8080\n45.32.10.21:8080\n")

        proxies = load_proxy_list(str(proxy_file))

        assert proxies == ["45.32.10.20:8080", "45.32.10.21:8080"]

    def test_ignora_lineas_vacias_y_comentarios(self, tmp_path):
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text(
            "# comentario\n\n45.32.10.20:8080\n\n# otro comentario\n45.32.10.21:8080\n"
        )

        proxies = load_proxy_list(str(proxy_file))

        assert proxies == ["45.32.10.20:8080", "45.32.10.21:8080"]

    def test_archivo_inexistente_lanza_error(self):
        with pytest.raises(ProxyError, match="no encontrado"):
            load_proxy_list("/ruta/inexistente/proxies.txt")

    def test_archivo_vacio_lanza_error(self, tmp_path):
        proxy_file = tmp_path / "empty.txt"
        proxy_file.write_text("# solo comentarios\n\n")

        with pytest.raises(ProxyError, match="vacío"):
            load_proxy_list(str(proxy_file))


class TestSelectProxy:
    def test_sin_proxy_ni_archivo_retorna_none(self):
        assert select_proxy() is None

    def test_proxy_fijo_se_parsea_correctamente(self):
        result = select_proxy(proxy="45.32.10.20:8080")
        assert result == {"server": "http://45.32.10.20:8080"}

    def test_proxy_file_elige_uno_de_la_lista(self, tmp_path):
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text("45.32.10.20:8080\n45.32.10.21:8080\n")

        result = select_proxy(proxy_file=str(proxy_file))

        assert result["server"] in {
            "http://45.32.10.20:8080",
            "http://45.32.10.21:8080",
        }

    def test_proxy_y_proxy_file_simultaneos_lanza_error(self, tmp_path):
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text("45.32.10.20:8080\n")

        with pytest.raises(ProxyError, match="al mismo tiempo"):
            select_proxy(proxy="45.32.10.99:8080", proxy_file=str(proxy_file))


class TestMaskCredentials:
    def test_enmascara_usuario_y_password(self):
        assert mask_credentials("user:secret@host:8080") == "***:***@host:8080"

    def test_enmascara_con_scheme(self):
        result = mask_credentials("http://user:secret@host:8080")
        assert result == "http://***:***@host:8080"

    def test_sin_credenciales_no_cambia(self):
        assert mask_credentials("host:8080") == "host:8080"
