"""Tests para el modo batch (src/batch.py)."""

import csv
import pytest

from src.batch import (
    load_batch_file,
    generate_batch_output_filename,
    combine_csv_files,
    BatchError,
)


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestLoadBatchFile:
    def test_carga_batch_valido(self, tmp_path):
        batch_file = tmp_path / "batch.csv"
        write_csv(
            batch_file,
            [
                {"query": "dentistas", "location": "Buenos Aires", "max": "50"},
                {"query": "abogados", "location": "Córdoba", "max": "30"},
            ],
            fieldnames=["query", "location", "max"],
        )

        searches = load_batch_file(str(batch_file), default_max=50)

        assert len(searches) == 2
        assert searches[0] == {"query": "dentistas", "location": "Buenos Aires", "max": 50}
        assert searches[1] == {"query": "abogados", "location": "Córdoba", "max": 30}

    def test_max_vacio_usa_default(self, tmp_path):
        batch_file = tmp_path / "batch.csv"
        write_csv(
            batch_file,
            [{"query": "gimnasios", "location": "Rosario", "max": ""}],
            fieldnames=["query", "location", "max"],
        )

        searches = load_batch_file(str(batch_file), default_max=75)

        assert searches[0]["max"] == 75

    def test_columna_max_opcional(self, tmp_path):
        batch_file = tmp_path / "batch.csv"
        write_csv(
            batch_file,
            [{"query": "dentistas", "location": "Buenos Aires"}],
            fieldnames=["query", "location"],
        )

        searches = load_batch_file(str(batch_file), default_max=50)

        assert searches[0]["max"] == 50

    def test_archivo_inexistente_lanza_error(self):
        with pytest.raises(BatchError, match="no encontrado"):
            load_batch_file("/ruta/inexistente/batch.csv", default_max=50)

    def test_archivo_vacio_lanza_error(self, tmp_path):
        batch_file = tmp_path / "empty.csv"
        batch_file.write_text("")

        with pytest.raises(BatchError, match="vacío"):
            load_batch_file(str(batch_file), default_max=50)

    def test_columnas_faltantes_lanza_error(self, tmp_path):
        batch_file = tmp_path / "batch.csv"
        write_csv(
            batch_file,
            [{"query": "dentistas"}],
            fieldnames=["query"],
        )

        with pytest.raises(BatchError, match="faltan columnas requeridas"):
            load_batch_file(str(batch_file), default_max=50)

    def test_filas_con_query_o_location_vacios_se_ignoran(self, tmp_path):
        batch_file = tmp_path / "batch.csv"
        write_csv(
            batch_file,
            [
                {"query": "dentistas", "location": "Buenos Aires", "max": "50"},
                {"query": "", "location": "Córdoba", "max": "30"},
                {"query": "abogados", "location": "", "max": "30"},
            ],
            fieldnames=["query", "location", "max"],
        )

        searches = load_batch_file(str(batch_file), default_max=50)

        assert len(searches) == 1
        assert searches[0]["query"] == "dentistas"

    def test_todas_las_filas_invalidas_lanza_error(self, tmp_path):
        batch_file = tmp_path / "batch.csv"
        write_csv(
            batch_file,
            [{"query": "", "location": "", "max": ""}],
            fieldnames=["query", "location", "max"],
        )

        with pytest.raises(BatchError, match="No se encontraron búsquedas válidas"):
            load_batch_file(str(batch_file), default_max=50)

    def test_max_no_numerico_usa_default(self, tmp_path):
        batch_file = tmp_path / "batch.csv"
        write_csv(
            batch_file,
            [{"query": "dentistas", "location": "Buenos Aires", "max": "muchos"}],
            fieldnames=["query", "location", "max"],
        )

        searches = load_batch_file(str(batch_file), default_max=50)

        assert searches[0]["max"] == 50


class TestGenerateBatchOutputFilename:
    def test_genera_nombre_valido(self):
        filename = generate_batch_output_filename("dentistas", "Buenos Aires")
        assert filename.startswith("resultados_dentistas_buenos_aires_")
        assert filename.endswith(".csv")


class TestCombineCsvFiles:
    def test_combina_multiples_csvs(self, tmp_path):
        fieldnames = ["nombre", "categoria"]

        csv1 = tmp_path / "a.csv"
        write_csv(csv1, [{"nombre": "Negocio 1", "categoria": "Dentista"}], fieldnames)

        csv2 = tmp_path / "b.csv"
        write_csv(csv2, [{"nombre": "Negocio 2", "categoria": "Abogado"}], fieldnames)

        combined = tmp_path / "combined.csv"
        total = combine_csv_files([str(csv1), str(csv2)], str(combined), fieldnames)

        assert total == 2
        assert combined.exists()

        with open(combined, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert rows[0]["nombre"] == "Negocio 1"
        assert rows[1]["nombre"] == "Negocio 2"

    def test_ignora_csv_faltante(self, tmp_path):
        fieldnames = ["nombre"]
        csv1 = tmp_path / "a.csv"
        write_csv(csv1, [{"nombre": "Negocio 1"}], fieldnames)

        combined = tmp_path / "combined.csv"
        total = combine_csv_files(
            [str(csv1), str(tmp_path / "no_existe.csv")], str(combined), fieldnames
        )

        assert total == 1

    def test_crea_directorio_padre_si_no_existe(self, tmp_path):
        fieldnames = ["nombre"]
        csv1 = tmp_path / "a.csv"
        write_csv(csv1, [{"nombre": "Negocio 1"}], fieldnames)

        combined = tmp_path / "nested" / "combined.csv"
        combine_csv_files([str(csv1)], str(combined), fieldnames)

        assert combined.exists()
