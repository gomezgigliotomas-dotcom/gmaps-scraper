# Google Maps Business Scraper

Scraper de Google Maps para encontrar negocios potenciales para una agencia de Google Ads. Exporta los datos a CSV listo para importar en Google Sheets.

## Qué extrae

| Campo | Descripción |
|-------|-------------|
| `nombre` | Nombre del negocio |
| `categoria` | Tipo de negocio según Google Maps |
| `rating` | Puntuación (1–5) |
| `cantidad_reviews` | Número de reseñas |
| `direccion` | Dirección completa |
| `telefono` | Teléfono de contacto |
| `sitio_web` | URL del sitio web (vacío = sin presencia digital) |
| `horario_estado` | Estado actual (Abierto / Cerrado) |

## Instalación

```bash
pip install playwright
playwright install chromium
```

## Uso

```bash
# Búsqueda básica
python scraper.py --query "dentistas" --location "Buenos Aires" --max 50

# Con más resultados
python scraper.py -q "restaurantes" -l "Palermo, Buenos Aires" -m 100

# Ver el browser mientras scrapea
python scraper.py -q "abogados" -l "Córdoba" --show-browser

# Guardar en archivo específico
python scraper.py -q "gimnasios" -l "Rosario" -o leads_rosario.csv
```

## Argumentos

| Argumento | Alias | Default | Descripción |
|-----------|-------|---------|-------------|
| `--query` | `-q` | requerido | Rubro o término a buscar |
| `--location` | `-l` | requerido | Ciudad o zona |
| `--max` | `-m` | `50` | Máximo de resultados |
| `--output` | `-o` | auto | Nombre del archivo CSV de salida |
| `--show-browser` | — | `false` | Muestra el browser durante el scraping |

El nombre del CSV se genera automáticamente si no se especifica:
```
resultados_{query}_{location}_{fecha}.csv
```

## Tips para agencias de Google Ads

- **Sin sitio web** (`sitio_web` vacío) → prospectos que necesitan presencia digital primero
- **Pocas reseñas + buen rating** → negocios establecidos con potencial de escalar con ads
- **Rubros con ticket alto** → dentistas, abogados, clínicas, constructoras, inmobiliarias
- Usá `--show-browser` si Google empieza a mostrar CAPTCHAs para resolverlos manualmente

## Notas

- Usa Playwright con Chromium headless
- El scraper respeta los tiempos de carga de Google Maps para evitar bloqueos
- Google Maps limita los resultados a ~120 por búsqueda; para más cobertura lanzá múltiples búsquedas con términos distintos y combiná los CSVs
