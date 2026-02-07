FROM python:3.12-slim

# Información del mantenedor
LABEL maintainer="Luis Chavez <lchavezpozo@gmail.com>"
LABEL description="Sistema de telemetría para básculas con MQTT"

# Configurar directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY pyproject.toml .
COPY README.md .

# Copiar código fuente
COPY src/ ./src/

# Instalar socat para crear puertos virtuales
RUN apt-get update && \
    apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/*

# Instalar el paquete
RUN pip install --no-cache-dir -e .

# Crear directorio para logs
RUN mkdir -p /var/log/scale-telemetry

# Variables de entorno por defecto
ENV MQTT_BROKER=localhost \
    MQTT_PORT=1883 \
    DEVICE_ID=scale-1 \
    SERIAL_PORT=/dev/ttyUSB0 \
    SERIAL_BAUDRATE=9600 \
    SERIAL_TIMEOUT=1.0 \
    PYTHONUNBUFFERED=1

# Healthcheck para verificar que el proceso está corriendo
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "scale_telemetry" || exit 1

# Comando por defecto
CMD ["scale-telemetry"]

