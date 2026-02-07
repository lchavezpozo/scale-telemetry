# CLAUDE.md

Este archivo provee guía a Claude Code (claude.ai/code) para trabajar con el código de este repositorio.

## Descripción del Proyecto

Scale Telemetry es un servicio IoT que lee datos de peso desde básculas industriales por puerto serial y los publica vía MQTT. Diseñado para la plataforma "pesanet". Requiere Python >= 3.12. Usa Poetry como build backend pero la gestión de dependencias se hace con pip (`pip install -e ".[dev]"`).

## Comandos

### Setup inicial
```bash
make setup            # Setup completo (crea .env, instala dependencias)
make dev              # Instala con dependencias de desarrollo (pip install -e ".[dev]")
```

### Testing
```bash
make test             # Ejecuta pytest con cobertura (reporte HTML en htmlcov/)
pytest tests/ -v      # Ejecutar tests directamente
pytest tests/test_serial_reader.py -v  # Ejecutar un archivo de tests
pytest tests/test_serial_reader.py::TestScaleReader::test_read_weight_success -v  # Ejecutar un test específico
```

### Linting y Formateo
```bash
make lint             # Ejecuta flake8 (max-line-length=100), black --check, mypy
make format           # Formatea con black (88 caracteres por línea)
```

### Ejecución local
```bash
make run              # Ejecuta el servicio (requiere puerto serial + broker MQTT)
make simulator-pty    # Simulador de báscula con PTY de Python (sin hardware)
make check-ports      # Lista puertos seriales disponibles
```

### Docker - Producción
```bash
make up               # Inicia servicios con docker-compose.yml
make down             # Detiene servicios
make restart          # Reinicia servicios
make build            # Construye las imágenes Docker
make logs             # Muestra logs de todos los servicios
make status           # Muestra estado de los contenedores
make docker-shell-telemetry  # Abre shell en el contenedor de telemetría
make docker-clean     # Limpia contenedores, volúmenes e imágenes
```

`docker-compose.yml` levanta solo el servicio `scale-telemetry`. Espera un broker MQTT externo (EMQX) y un puerto serial real o socat. Usa `privileged: true` para acceder a puertos serial. La red es bridge (`scale-network`).

### Docker - Desarrollo (con simulador)
```bash
docker-compose -f docker-compose.dev.yml up --build    # Levanta con simulador de báscula
docker-compose -f docker-compose.dev.yml down           # Detiene todo
```

`docker-compose.dev.yml` incluye un contenedor `scale-simulator` (Alpine) que genera datos de peso via named pipe (FIFO) en `/shared/scale_pipe`. El servicio de telemetría usa `entrypoint-dev.sh` para leer desde ese pipe. Variables del simulador:
- `SIMULATOR_RANDOM=true/false` — peso aleatorio o fijo
- `SIMULATOR_WEIGHT=120` — peso fijo en kg (cuando `SIMULATOR_RANDOM=false`)
- El broker MQTT apunta a `host.docker.internal:8083` (WebSocket) para alcanzar EMQX en el host

### Testing MQTT
```bash
make mqtt-test        # Envía comando get_weight (requiere mosquitto_pub)
make mqtt-subscribe   # Suscribirse a respuestas
make mqtt-client-test # Ejecuta cliente de prueba Python (examples/mqtt_test_client.py)
```

### Otros
```bash
bash docker-run.sh    # Script interactivo de setup Docker (crea .env, verifica puertos, construye y levanta)
make clean            # Limpia __pycache__, .pytest_cache, htmlcov, logs
```

## Arquitectura

```
ScaleTelemetryService (main.py)
       │
       ├── ScaleReader (serial_reader.py)
       │     └── Lee peso del puerto serial con pyserial
       │     └── Parsea valores con regex (extrae primer número de la línea)
       │
       └── ScaleMQTTClient (mqtt_client.py)
             └── Se suscribe al tópico de comandos, publica respuestas
             └── Usa paho-mqtt con transporte WebSocket (ws://<broker>:<port>/mqtt)
             └── Patrón de callbacks: _on_connect, _on_message, _on_disconnect
```

**Transporte MQTT:** WebSocket (no TCP raw). El cliente se conecta a `ws://<broker>:<port>/mqtt`.

**Tópicos MQTT:**
- Comando: `pesanet/devices/{device_id}/command` (escucha `{"command": "get_weight"}`)
- Respuesta: `pesanet/devices/{device_id}/response` (publica JSON con `deviceId`, `weight`, `status`, `message`, `timestamp`)

**Configuración:** Via variables de entorno o archivo `.env`. Dataclasses en `config.py` (`MQTTConfig`, `SerialConfig`) leen env vars al importarse con `os.getenv`. Nota: `config.py` tiene credenciales por defecto hardcodeadas — siempre sobreescribir via env vars.

**Flujo:** Mensaje MQTT llega -> `_on_message` parsea JSON -> despacha a `_handle_get_weight` -> llama `weight_callback` (que llama a `ScaleReader.read_weight()`) -> publica respuesta JSON.

## Convenciones del Código

- Comentarios, docstrings y mensajes de log están en **español**. Mantener esta convención.
- Layout `src/` con paquete `scale_telemetry`.
- Configuración usa dataclasses con valores por defecto desde env vars (sin archivos de config).
- Tests usan `pytest` con `unittest.mock` (no fixtures de `pytest-mock`). Se organizan en clases (ej: `TestScaleReader`) con fixtures de pytest para config y mocks.
- Dependencias de hardware (puerto serial, broker MQTT) se mockean en tests via `@patch` y `MagicMock`.
