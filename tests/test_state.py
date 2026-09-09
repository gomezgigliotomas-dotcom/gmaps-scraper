"""Tests para persistencia de estado / resume (src/state.py)."""

from pathlib import Path
import pytest

from src.state import get_state_path, load_state, save_state, clear_state


class TestGetStatePath:
    def test_genera_path_estable_para_misma_busqueda(self, tmp_path):
        p1 = get_state_path("dentistas", "Buenos Aires", 50, state_dir=tmp_path)
        p2 = get_state_path("dentistas", "Buenos Aires", 50, state_dir=tmp_path)
        assert p1 == p2

    def test_busquedas_distintas_generan_paths_distintos(self, tmp_path):
        p1 = get_state_path("dentistas", "Buenos Aires", 50, state_dir=tmp_path)
        p2 = get_state_path("restaurantes", "Buenos Aires", 50, state_dir=tmp_path)
        assert p1 != p2

    def test_es_insensible_a_mayusculas(self, tmp_path):
        p1 = get_state_path("Dentistas", "Buenos Aires", 50, state_dir=tmp_path)
        p2 = get_state_path("dentistas", "buenos aires", 50, state_dir=tmp_path)
        assert p1 == p2

    def test_max_results_distinto_genera_path_distinto(self, tmp_path):
        p1 = get_state_path("dentistas", "Buenos Aires", 50, state_dir=tmp_path)
        p2 = get_state_path("dentistas", "Buenos Aires", 100, state_dir=tmp_path)
        assert p1 != p2


class TestSaveAndLoadState:
    def test_guarda_y_carga_estado(self, tmp_path):
        state_path = tmp_path / "test_state.json"
        results = [{"nombre": "Negocio 1"}, {"nombre": "Negocio 2"}]

        save_state(
            state_path,
            query="dentistas",
            location="Buenos Aires",
            max_results=50,
            output_file="out.csv",
            results=results,
            processed_count=2,
        )

        loaded = load_state(state_path)

        assert loaded is not None
        assert loaded["query"] == "dentistas"
        assert loaded["location"] == "Buenos Aires"
        assert loaded["processed_count"] == 2
        assert loaded["results"] == results

    def test_load_state_inexistente_retorna_none(self, tmp_path):
        assert load_state(tmp_path / "no_existe.json") is None

    def test_load_state_corrupto_retorna_none(self, tmp_path):
        state_path = tmp_path / "corrupto.json"
        state_path.write_text("{ esto no es json valido")

        assert load_state(state_path) is None

    def test_save_state_preserva_created_at_original(self, tmp_path):
        state_path = tmp_path / "state.json"

        save_state(
            state_path, "q", "l", 10, "out.csv", [{"nombre": "A"}], 1
        )
        first = load_state(state_path)

        save_state(
            state_path, "q", "l", 10, "out.csv",
            [{"nombre": "A"}, {"nombre": "B"}], 2,
        )
        second = load_state(state_path)

        assert first["created_at"] == second["created_at"]
        assert second["processed_count"] == 2

    def test_save_state_crea_directorio_padre(self, tmp_path):
        state_path = tmp_path / "nested" / "dir" / "state.json"

        save_state(state_path, "q", "l", 10, "out.csv", [], 0)

        assert state_path.exists()


class TestClearState:
    def test_elimina_archivo_existente(self, tmp_path):
        state_path = tmp_path / "state.json"
        save_state(state_path, "q", "l", 10, "out.csv", [], 0)
        assert state_path.exists()

        clear_state(state_path)

        assert not state_path.exists()

    def test_no_lanza_error_si_no_existe(self, tmp_path):
        state_path = tmp_path / "no_existe.json"
        clear_state(state_path)  # no debe lanzar excepción
