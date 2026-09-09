# Google Maps Business Scraper

Scraper profesional de Google Maps para encontrar negocios potenciales para una agencia de Google Ads. Exporta los datos a CSV listo para importar en Google Sheets.

**Versión 2.3.2** ✨ - Logging profesional, retry automático, proxies, resume, batch de búsquedas y Docker.

## Qué extrae

| Campo | Descripción |
|-------|-------------|
| `nombre` | Nombre del negocio |
| `categoria` | Tipo de negocio según Google Maps |
| `rating` | Puntuación (1–5) |
| `cantidad_reviews` | Número de reseñas (puede venir vacío — ver nota abajo) |
| `direccion` | Dirección completa |
| `telefono` | Teléfono de contacto |
| `sitio_web` | URL del sitio web (vacío = sin presencia digital) |
| `horario_estado` | Estado actual (Abierto / Cerrado) |

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/gomezgigliotomas-dotcom/gmaps-scraper.git
cd gmaps-scraper

# Instalar dependencias
pip install -r requirements.txt
playwright install chromium
```

## Uso

### Búsqueda básica
```bash
python scraper.py --query "dentistas" --location "Buenos Aires" --max 50
```

### Con más resultados
```bash
python scraper.py -q "restaurantes" -l "Palermo, Buenos Aires" -m 100
```

### Ver el browser mientras scrapea
```bash
python scraper.py -q "abogados" -l "Córdoba" --show-browser
```

### Guardar en archivo específico
```bash
python scraper.py -q "gimnasios" -l "Rosario" -o leads_rosario.csv
```

### Con logging detallado
```bash
python scraper.py -q "dentistas" -l "Buenos Aires" --log-level DEBUG --log-file scraper.log
```

### Con configuración custom (selectores/timeouts propios)
```bash
python scraper.py -q "dentistas" -l "Buenos Aires" --config config/mi_config.json
```

### Con proxy fijo (evitar bloqueos)
```bash
python scraper.py -q "dentistas" -l "Buenos Aires" --proxy "http://user:pass@45.32.10.20:8080"
```

### Con rotación de proxies (recomendado para volumen alto)
```bash
# 1. Copiá el archivo de ejemplo y completá tus proxies reales
cp proxies.example.txt proxies.txt

# 2. Corré el scraper apuntando al archivo — elige uno al azar en cada corrida
python scraper.py -q "dentistas" -l "Buenos Aires" --proxy-file proxies.txt
```

### Retomar un scraping interrumpido
```bash
# Si se cortó a mitad de camino (Ctrl+C, error, bloqueo), volvé a correr
# el mismo comando agregando --resume: continúa desde donde quedó
python scraper.py -q "dentistas" -l "Buenos Aires" -m 100 --resume
```

### Múltiples búsquedas en batch
```bash
# 1. Copiá el archivo de ejemplo y armá tu lista de búsquedas
cp batch.example.csv batch.csv

# 2. Corré el batch — genera un CSV por búsqueda
python scraper.py --batch-file batch.csv

# 3. (Opcional) Combiná todos los CSVs del batch en uno solo
python scraper.py --batch-file batch.csv --combine-output leads_todos.csv
```

## Argumentos

| Argumento | Alias | Default | Descripción |
|-----------|-------|---------|-------------|
| `--query` | `-q` | requerido* | Rubro o término a buscar |
| `--location` | `-l` | requerido* | Ciudad o zona |
| `--max` | `-m` | `50` | Máximo de resultados por búsqueda |
| `--output` | `-o` | auto | Nombre del archivo CSV de salida (no aplica con `--batch-file`) |
| `--show-browser` | — | `false` | Muestra el browser durante el scraping |
| `--log-level` | — | `INFO` | Nivel de logging (DEBUG, INFO, WARNING, ERROR) |
| `--log-file` | — | — | Archivo para guardar logs |
| `--config` | — | `config/default.json` | Path a config JSON alternativo |
| `--proxy` | — | — | Proxy fijo (ej: `http://user:pass@host:port`) |
| `--proxy-file` | — | — | Archivo con lista de proxies; rota al azar en cada corrida |
| `--resume` | — | `false` | Retoma un scraping interrumpido en vez de arrancar de cero |
| `--batch-file` | — | — | CSV con múltiples búsquedas (columnas: `query,location,max`) |
| `--combine-output` | — | — | Con `--batch-file`: combina todos los CSVs en uno solo |

\* `--query`/`--location` son requeridos salvo que uses `--batch-file`

El nombre del CSV se genera automáticamente si no se especifica:
```
resultados_{query}_{location}_{fecha}.csv
```

## ✨ Novedades en v2.0

### 🏗️ Mejor Estructura
- **Modularizado**: Separado en `logger.py`, `extractors.py`, `scraper.py`, `main.py`
- **Mantenible**: Cada módulo tiene una responsabilidad clara
- **Escalable**: Fácil agregar nuevas funcionalidades

### 📝 Type Hints
- Mejor autocompletar en IDEs
- Código más legible y menos propenso a errores
- Documentación intrínseca en el código

### 🔍 Logging Profesional
- Logging a consola y archivo
- Niveles configurables (DEBUG, INFO, WARNING, ERROR)
- Timestamps y contexto detallado
- Fácil debuggear qué salió mal

### 🛡️ Mejor Manejo de Errores
- Excepciones capturadas y loggeadas correctamente
- Validación de entrada
- Mensajes de error más informativos
- Continuación del scraping en caso de fallos parciales

## ✨ Novedades en v2.1

### 🔄 Retry automático con backoff exponencial
- Si falla la extracción de un negocio (timeout, elemento no cargó), se reintenta automáticamente hasta 3 veces (configurable) antes de descartarlo
- Espera creciente entre reintentos (1s → 2s → 4s) para no saturar la página
- Menos leads perdidos por fallos temporales de red o carga

### ⚙️ Configuración editable en JSON
- Selectores CSS, timeouts y valores default ahora viven en `config/default.json`
- Si Google Maps cambia sus clases CSS, se edita el JSON sin tocar código Python
- Se puede pasar un config alternativo con `--config` (útil para ambientes o experimentos distintos)

### ✅ Validación de entrada avanzada
- `--query`/`--location`: rechaza vacíos, caracteres de control y separadores de path
- `--output`: exige extensión `.csv` y verifica permisos de escritura en el directorio
- `--config`: verifica que el archivo exista antes de arrancar el scraping
- `--max`: avisa si se pide más del límite práctico de Google Maps (~120)

### 🧪 Tests automatizados (pytest)
- 37 tests cubriendo extracción de datos, validaciones del CLI, config y retry logic
- Los tests de extracción usan mocks de Playwright — no necesitan Google Maps real ni red
- Correr con: `pytest -v`

## ✨ Novedades en v2.2

### 🌐 Soporte de Proxies (evitar bloqueos/CAPTCHAs)

Google detecta scraping principalmente por la IP que hace las requests. Si corrés muchas búsquedas seguidas desde tu misma IP, Google puede empezar a mostrar CAPTCHAs o bloquearla temporalmente.

**Cómo funciona:**
- `--proxy "http://user:pass@host:port"` — usa un proxy fijo para toda la corrida
- `--proxy-file proxies.txt` — elige un proxy al azar de una lista en cada corrida (rotación)
- Sin ninguno de los dos, el scraper corre con conexión directa (igual que antes)

**Formatos de proxy soportados:**
```
host:port
user:pass@host:port
http://host:port
http://user:pass@host:port
socks5://host:port
```

**Seguridad:**
- `proxies.txt` está en `.gitignore` — nunca se sube al repo por accidente
- Las contraseñas de proxy nunca aparecen en texto plano en los logs (se enmascaran como `***:***@host:port`)
- Usá `proxies.example.txt` como plantilla

**¿Cuándo usarlo?**
- Volumen bajo/ocasional (prospección manual para tu propia agencia) → probablemente no lo necesites, `--show-browser` alcanza para resolver algún CAPTCHA ocasional
- Volumen alto o corridas automatizadas frecuentes → **recomendado**, evita que tu IP quede bloqueada

## ✨ Novedades en v2.3

### ⏯️ Resume (retomar scraping interrumpido)

Si el scraper se corta a mitad de camino (Ctrl+C, un error, Google bloqueando), no hace falta arrancar de cero.

- Cada búsqueda (`query` + `location` + `max`) guarda su progreso incrementalmente en `.gmaps_state/`
- Volvé a correr el mismo comando agregando `--resume`: continúa desde el último negocio procesado
- Al completarse exitosamente, el estado se borra automáticamente
- `.gmaps_state/` está en `.gitignore`

```bash
python scraper.py -q "dentistas" -l "Buenos Aires" -m 100
# ...se corta a mitad de camino...
python scraper.py -q "dentistas" -l "Buenos Aires" -m 100 --resume
# retoma desde donde quedó, no repite negocios ya extraídos
```

### 📦 Batch (múltiples búsquedas en una corrida)

Para prospectar varios rubros/ciudades sin ejecutar el comando uno por uno:

- `--batch-file batch.csv` — CSV con columnas `query,location,max` (la columna `max` es opcional por fila)
- Cada búsqueda genera su propio CSV con nombre automático
- `--combine-output leads_todos.csv` — además, combina todos los resultados en un único CSV
- `--resume` también funciona en modo batch: si se corta a mitad del batch, retoma la búsqueda que quedó a medias

```csv
query,location,max
dentistas,Buenos Aires,50
abogados,Córdoba,30
restaurantes,"Palermo, Buenos Aires",100
```

### 🐳 Docker

El proyecto incluye `Dockerfile` y `docker-compose.yml` basados en la imagen oficial de Playwright (con Chromium ya instalado), para no depender de tener Python/Playwright configurados localmente.

```bash
# Build
docker build -t gmaps-scraper .

# Correr una búsqueda (resultados quedan en ./output)
docker run --rm -v "$(pwd)/output:/app/output" gmaps-scraper \
  --query "dentistas" --location "Buenos Aires" --max 50 --output /app/output/resultados.csv

# O con docker compose (editá el `command` en docker-compose.yml)
docker compose run --rm scraper --query "dentistas" --location "Buenos Aires" -o /app/output/resultados.csv
```

> **Nota:** no se puede correr con `--show-browser` dentro del contenedor (no hay entorno gráfico) — usá esa opción solo para debugging local.

## 🐛 v2.3.1 — Fixes de corridas reales contra Google Maps

Todo lo de v2.3 se probó corriendo el scraper contra Google Maps real (no solo con mocks), lo que reveló varios bugs que no aparecían en los tests unitarios:

- **El primer resultado del feed se perdía siempre.** El selector de items matcheaba por error el carrusel de filtros de Google ("Horario", "Rating", etc.), que casualmente comparte estructura con un resultado real. Ahora el selector filtra explícitamente por `role="article"`, que es como Google marca cada negocio.
- **`cantidad_reviews` a veces mostraba el mismo valor que `rating`.** El selector tomaba por error el aria-label de las "estrellas visuales" (`"4.9 estrellas"`) como si fuera un conteo de reseñas. Ahora se descarta explícitamente y el campo queda vacío si Google no expone el conteo real (ver Troubleshooting).
- **`direccion`, `telefono` y `horario_estado` traían íconos de fuente pegados al texto** (caracteres invisibles + saltos de línea al principio/final). Se limpia el texto y se prefiere el `aria-label` del elemento (más estable) sobre su texto visible.
- **Los logs de `scraper.py`, `retry.py`, etc. no se mostraban** — quedaban en un logger sin conectar al configurado por `--log-level`/`--log-file`. Se corrigió la jerarquía de logging.
- **`--resume` podía duplicar negocios** si el orden de resultados de Google cambiaba levemente entre la corrida original y la retomada. Ahora se deduplica por nombre + dirección.

### v2.3.2 — Fix de build de Docker

Probé el `docker build` + `docker run` + `docker compose run` de punta a punta (ya no solo revisado a mano) y encontré un bug real: `requirements.txt` no fijaba la versión de `playwright`, así que `pip install` traía la última versión disponible — pero la imagen base del `Dockerfile` trae Chromium preinstalado para una versión puntual. El mismatch hacía que el contenedor fallara al lanzar el browser (`Executable doesn't exist`).

**Fix:** `playwright==1.62.0` fijado en `requirements.txt`, coincidiendo exactamente con el tag de la imagen base (`v1.62.0-jammy`) en el `Dockerfile`. Si en el futuro actualizás una versión, hay que actualizar la otra — queda documentado con un comentario en ambos archivos.

Verificado con una búsqueda real dentro del contenedor (`docker run` y `docker compose run`), con el volumen de `output/` accesible desde el host.

## Tips para agencias de Google Ads

- **Sin sitio web** (`sitio_web` vacío) → prospectos que necesitan presencia digital primero
- **Pocas reseñas + buen rating** → negocios establecidos con potencial de escalar con ads
- **Rubros con ticket alto** → dentistas, abogados, clínicas, constructoras, inmobiliarias
- Usá `--show-browser` si Google empieza a mostrar CAPTCHAs para resolverlos manualmente
- Usá `--log-level DEBUG` para troubleshooting
- Usá `--proxy-file` si vas a correr el scraper seguido o en volumen — reduce mucho el riesgo de bloqueo

## Notas Técnicas

- ✅ Usa Playwright con Chromium headless (más rápido y confiable que Selenium)
- ✅ El scraper respeta los tiempos de carga de Google Maps para evitar bloqueos
- ✅ Google Maps limita los resultados a ~120 por búsqueda
- ✅ Para más cobertura, ejecuta múltiples búsquedas con términos distintos
- ✅ Los selectores CSS y timeouts viven en `config/default.json` para fácil mantenimiento
- ✅ Extracción de cada negocio reintenta automáticamente ante fallos temporales
- ✅ El progreso se guarda incrementalmente — un corte a mitad de camino no pierde lo ya extraído

## Estructura del Proyecto

```
gmaps-scraper/
├── src/
│   ├── __init__.py         # Exporta módulo
│   ├── main.py             # CLI entrypoint + validaciones + orquestación batch
│   ├── scraper.py          # Lógica principal de scraping
│   ├── extractors.py       # Extracción de datos (type hints)
│   ├── retry.py            # Retry con exponential backoff
│   ├── config.py           # Carga/validación de config JSON
│   ├── proxy.py            # Parseo y rotación de proxies
│   ├── state.py            # Persistencia de estado (--resume)
│   ├── batch.py            # Carga y ejecución de --batch-file
│   └── logger.py           # Setup de logging profesional
├── config/
│   └── default.json        # Selectores, timeouts, retry, defaults
├── tests/
│   ├── test_main.py        # Tests de validación del CLI
│   ├── test_config.py      # Tests de carga de config
│   ├── test_retry.py       # Tests de retry logic
│   ├── test_proxy.py       # Tests de parseo/rotación de proxies
│   ├── test_state.py       # Tests de persistencia/resume
│   ├── test_batch.py       # Tests de carga/combinación de batch
│   └── test_extractors.py  # Tests de extracción (con mocks)
├── proxies.example.txt      # Plantilla para lista de proxies
├── batch.example.csv        # Plantilla para múltiples búsquedas
├── Dockerfile                # Imagen basada en Playwright oficial
├── docker-compose.yml        # Atajo para correr con volúmenes montados
├── .dockerignore
├── scraper.py               # Wrapper para compatibilidad
├── requirements.txt         # Dependencias de producción
├── requirements-dev.txt     # + pytest, pytest-asyncio
├── pytest.ini                # Config de pytest
└── README.md                # Este archivo
```

## Correr los tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

## Troubleshooting

### "No se encontró el panel de resultados"
- La búsqueda puede no ser válida
- Google puede estar bloqueando por demasiadas requests
- Intenta con `--show-browser` para ver qué pasa
- Aumenta el timeout esperando resultados

### CAPTCHA
- Google Maps muestra CAPTCHAs si detecta scraping automatizado
- Usa `--show-browser` para resolverlos manualmente
- Espera un tiempo antes de volver a intentar
- Considera usar delays más largos
- Si es recurrente, pasá a usar `--proxy-file` con rotación de IPs

### Errores de proxy ("Formato de proxy inválido", conexión rechazada)
- Verificá el formato: `host:port` o `user:pass@host:port` (ver sección de Proxies)
- Si tu proxy requiere autenticación, confirmá que el `user:pass` esté bien escrito
- Probá el proxy fuera del scraper primero (ej: `curl -x http://user:pass@host:port https://google.com`)

### Selectores no funcionan
- Google Maps actualiza sus clases CSS ocasionalmente
- Abre un issue en GitHub si los selectores dejan de funcionar
- Puedes debuggear con `--log-level DEBUG`

### `cantidad_reviews` viene vacío
- Es esperado en muchos casos: Google Maps no siempre expone el conteo de reseñas en el panel rápido de detalle (solo muestra el rating con estrellas). El scraper deja el campo vacío en vez de inventar un valor — no es un bug, es un dato que Google no está mostrando en ese momento/negocio.

### El scraping se cortó a mitad de camino
- Volvé a correr el mismo comando (misma query/location/max) agregando `--resume`
- Si el resultado sigue siendo incompleto, revisá `.gmaps_state/` — puede que el archivo de estado se haya corrompido; borralo y arrancá de cero

### Docker: "unable to connect to display" o similar con --show-browser
- El contenedor no tiene entorno gráfico; no uses `--show-browser` dentro de Docker
- Para resolver CAPTCHAs manualmente, corré el scraper localmente (fuera de Docker) esa vez puntual

## Roadmap Futuro

- [x] Retry logic con exponential backoff
- [x] Configuración editable en JSON
- [x] Tests automatizados
- [x] Proxy support para evitar bloqueos
- [x] Persistencia de estado (reanudar scraping)
- [x] Soporte para múltiples ubicaciones en batch
- [x] Docker setup

## Licencia

MIT - Libre para usar en proyectos personales y comerciales

## Autor

Tomás Goez Giglio - [GitHub](https://github.com/gomezgigliotomas-dotcom)
