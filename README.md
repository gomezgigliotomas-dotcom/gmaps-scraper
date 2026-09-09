# Google Maps Business Scraper

Scraper profesional de Google Maps para encontrar negocios potenciales para una agencia de Google Ads. Exporta los datos a CSV listo para importar en Google Sheets.

**Versión 2.0** ✨ - Refactorizado con logging profesional, type hints y mejor estructura.

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

## Tips para agencias de Google Ads

- **Sin sitio web** (`sitio_web` vacío) → prospectos que necesitan presencia digital primero
- **Pocas reseñas + buen rating** → negocios establecidos con potencial de escalar con ads
- **Rubros con ticket alto** → dentistas, abogados, clínicas, constructoras, inmobiliarias
- Usá `--show-browser` si Google empieza a mostrar CAPTCHAs para resolverlos manualmente
- Usá `--log-level DEBUG` para troubleshooting

## Notas Técnicas

- ✅ Usa Playwright con Chromium headless (más rápido y confiable que Selenium)
- ✅ El scraper respeta los tiempos de carga de Google Maps para evitar bloqueos
- ✅ Google Maps limita los resultados a ~120 por búsqueda
- ✅ Para más cobertura, ejecuta múltiples búsquedas con términos distintos
- ✅ Los selectores CSS están centralizados en `src/extractors.py` para fácil mantenimiento

## Estructura del Proyecto

```
gmaps-scraper/
├── src/
│   ├── __init__.py         # Exporta módulo
│   ├── main.py             # CLI entrypoint
│   ├── scraper.py          # Lógica principal de scraping
│   ├── extractors.py       # Extracción de datos (type hints)
│   └── logger.py           # Setup de logging profesional
├── scraper.py              # Wrapper para compatibilidad
├── requirements.txt        # Dependencias
└── README.md              # Este archivo
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

### Selectores no funcionan
- Google Maps actualiza sus clases CSS ocasionalmente
- Abre un issue en GitHub si los selectores dejan de funcionar
- Puedes debuggear con `--log-level DEBUG`

## Roadmap Futuro

- [ ] Retry logic con exponential backoff
- [ ] Proxy support para evitar bloqueos
- [ ] Persistencia de estado (reanudar scraping)
- [ ] Soporte para múltiples ubicaciones en batch
- [ ] Docker setup
- [ ] Tests automatizados

## Licencia

MIT - Libre para usar en proyectos personales y comerciales

## Autor

Tomás Goez Giglio - [GitHub](https://github.com/gomezgigliotomas-dotcom)
