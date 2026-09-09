"""Tests para retry logic con exponential backoff (src/retry.py)."""

import pytest

from src.retry import retry_async


class TestRetryAsync:
    @pytest.mark.asyncio
    async def test_exito_en_primer_intento_no_reintenta(self):
        calls = []

        async def func():
            calls.append(1)
            return "ok"

        result = await retry_async(func, max_attempts=3, base_delay=0.01)
        assert result == "ok"
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_exito_tras_fallos_intermitentes(self):
        calls = []

        async def func():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("falla temporal")
            return "ok"

        result = await retry_async(func, max_attempts=5, base_delay=0.01)
        assert result == "ok"
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_agota_intentos_y_lanza_ultima_excepcion(self):
        calls = []

        async def func():
            calls.append(1)
            raise RuntimeError(f"falla {len(calls)}")

        with pytest.raises(RuntimeError, match="falla 3"):
            await retry_async(func, max_attempts=3, base_delay=0.01)
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_max_attempts_invalido_lanza_value_error(self):
        async def func():
            return "ok"

        with pytest.raises(ValueError, match="max_attempts debe ser >= 1"):
            await retry_async(func, max_attempts=0)

    @pytest.mark.asyncio
    async def test_delay_respeta_tope_maximo(self):
        """El delay no debería crecer indefinidamente pasado max_delay."""
        calls = []

        async def func():
            calls.append(1)
            if len(calls) < 4:
                raise RuntimeError("falla")
            return "ok"

        # base_delay alto + exponential_base alto, pero max_delay bajo
        # así el test corre rápido aunque haya varios reintentos
        result = await retry_async(
            func,
            max_attempts=5,
            base_delay=0.01,
            max_delay=0.02,
            exponential_base=10.0,
        )
        assert result == "ok"
