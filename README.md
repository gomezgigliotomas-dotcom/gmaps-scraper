# Google Maps Business Scraper

Scraper profesional de Google Maps para encontrar negocios potenciales para una agencia de Google Ads. Exporta los datos a CSV listo para importar en Google Sheets.

**Versión 2.2** ✨ - Logging profesional, type hints, retry automático, config editable, tests y soporte de proxies.

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

## Argumentos

| Argumento | Alias | Default | Descripción |
|-----------|-------|---------|-------------|
| `--query` | `-q` | requerido | Rubro o término a buscar |
| `--location` | `-l` | requerido | Ciudad o zona |
| `--max` | `-m` | `50` | Máximo de resultados |
| `--output` | `-o` | auto | Nombre del archivo CSV de salida |
| `--show-browser` | — | `false` | Muestra el browser durante el scraping |
| `--log-level` | — | `INFO` | Nivel de logging (DEBUG, INFO, WARNING, ERROR) |
| `--log-file` | — | — | Archivo para guardar logs |
| `--config` | — | `config/default.json` | Path a config JSON alternativo |
| `--proxy` | — | — | Proxy fijo (ej: `http://user:pass@host:port`) |
| `--proxy-file` | — | — | Archivo con lista de proxies; rota al azar en cada corrida |

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

## Estructura del Proyecto

```
gmaps-scraper/
├── src/
│   ├── __init__.py         # Exporta módulo
│   ├── main.py             # CLI entrypoint + validaciones
│   ├── scraper.py          # Lógica principal de scraping
│   ├── extractors.py       # Extracción de datos (type hints)
│   ├── retry.py            # Retry con exponential backoff
│   ├── config.py           # Carga/validación de config JSON
│   ├── proxy.py            # Parseo y rotación de proxies
│   └── logger.py           # Setup de logging profesional
├── config/
│   └── default.json        # Selectores, timeouts, retry, defaults
├── tests/
│   ├── test_main.py        # Tests de validación del CLI
│   ├── test_config.py      # Tests de carga de config
│   ├── test_retry.py       # Tests de retry logic
│   ├── test_proxy.py       # Tests de parseo/rotación de proxies
│   └── test_extractors.py  # Tests de extracción (con mocks)
├── proxies.example.txt      # Plantilla para lista de proxies
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

## Roadmap Futuro

- [x] Retry logic con exponential backoff
- [x] Configuración editable en JSON
- [x] Tests automatizados
- [x] Proxy support para evitar bloqueos
- [ ] Persistencia de estado (reanudar scraping)
- [ ] Soporte para múltiples ubicaciones en batch
- [ ] Docker setup

## Licencia

MIT - Libre para usar en proyectos personales y comerciales

## Autor

Tomás Goez Giglio - [GitHub](https://github.com/gomezgigliotomas-dotcom)
