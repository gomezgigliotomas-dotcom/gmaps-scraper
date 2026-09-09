# Imagen oficial de Playwright con Python y navegadores preinstalados
# (evita tener que instalar Chromium + dependencias del sistema a mano)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Instalar dependencias primero para aprovechar el cache de capas de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Directorio para resultados, montable como volumen desde el host
RUN mkdir -p /app/output

# Usuario no-root (más seguro, y coincide con la práctica de la imagen base)
RUN chown -R pwuser:pwuser /app
USER pwuser

ENTRYPOINT ["python", "scraper.py"]
CMD ["--help"]
