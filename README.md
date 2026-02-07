# Scale Telemetry 🏷️⚖️

Sistema de telemetría para básculas que permite controlar y leer el peso mediante comandos MQTT.

---

⚡ **[Inicio Rápido (5 minutos)](QUICKSTART.md)** | 🐳 **[Guía Docker](DOCKER.md)** | 🔌 **[Configuración EMQX](EMQX.md)** | 📝 **[Ejemplos](examples/README.md)**

---

## Características

- 📡 Comunicación MQTT con suscripción a comandos
- ⚖️ Lectura de peso desde puerto serial
- 🔄 Respuestas automáticas en formato JSON
- 🔧 Configuración mediante variables de entorno
- 📝 Logging completo de operaciones

## Arquitectura

El sistema se compone de tres módulos principales:

1. **Serial Reader**: Lee el peso desde la báscula conectada por puerto serial
2. **MQTT Client**: Maneja la comunicación MQTT (comandos y respuestas)
3. **Main Service**: Orquesta ambos componentes

## Instalación

> 💡 **¿Primera vez?** Lee la [Guía de Inicio Rápido](QUICKSTART.md)

### Opción 1: Docker (Recomendado) 🐳

La forma más fácil de ejecutar el sistema es usando Docker:

```bash
# Método 1: Script automático
chmod +x docker-run.sh
./docker-run.sh

# Método 2: Con Make
make setup
make up

# Método 3: Docker Compose directo
docker-compose up -d
```

Ver la [Guía completa de Docker](DOCKER.md) para más detalles.

### Opción 2: Instalación Local

#### Requisitos

- Python 3.12+
- Báscula conectada por puerto serial
- Broker MQTT accesible (EMQX, Mosquitto, etc.)

#### Pasos de instalación

```bash
# Clonar el repositorio
git clone <repository-url>
cd scale-telemetry

# Instalar el paquete
pip install -e .
```

## Configuración

Copia el archivo de configuración de ejemplo y ajusta los valores:

```bash
cp config.env.example config.env
```

### Variables de entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `MQTT_BROKER` | Dirección del broker MQTT | `localhost` |
| `MQTT_PORT` | Puerto del broker MQTT | `1883` |
| `MQTT_USERNAME` | Usuario MQTT (opcional) | - |
| `MQTT_PASSWORD` | Contraseña MQTT (opcional) | - |
| `DEVICE_ID` | ID del dispositivo | `scale-1` |
| `SERIAL_PORT` | Puerto serial de la báscula | `/dev/ttyUSB0` |
| `SERIAL_BAUDRATE` | Velocidad del puerto serial | `9600` |
| `SERIAL_TIMEOUT` | Timeout de lectura serial (seg) | `1.0` |

## Uso

### Iniciar el servicio

```bash
# Usando el comando instalado
scale-telemetry

# O directamente con Python
python -m scale_telemetry.main
```

### Protocolo MQTT

#### Tópico de comandos

**Tópico**: `pesanet/devices/<device_id>/command`

**Formato del comando**:
```json
{
  "command": "get_weight"
}
```

#### Tópico de respuestas

**Tópico**: `pesanet/devices/<device_id>/response`

**Formato de respuesta exitosa**:
```json
{
  "deviceId": "scale-1",
  "weight": 45.3,
  "status": "ok",
  "message": "Peso obtenido correctamente",
  "timestamp": 1698765433000
}
```

**Formato de respuesta con error**:
```json
{
  "deviceId": "scale-1",
  "weight": null,
  "status": "error",
  "message": "Error al leer peso: <descripción del error>",
  "timestamp": 1698765433000
}
```

### Ejemplo con mosquitto

```bash
# Suscribirse a las respuestas
mosquitto_sub -h localhost -t "pesanet/devices/scale-1/response"

# Enviar comando (en otra terminal)
mosquitto_pub -h localhost -t "pesanet/devices/scale-1/command" -m '{"command":"get_weight"}'
```

### Ejemplo con Python

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    response = json.loads(msg.payload.decode())
    print(f"Peso recibido: {response['weight']} kg")
    print(f"Status: {response['status']}")
    print(f"Mensaje: {response['message']}")

# Configurar cliente
client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883)

# Suscribirse a respuestas
client.subscribe("pesanet/devices/scale-1/response")
client.loop_start()

# Enviar comando
command = {"command": "get_weight"}
client.publish("pesanet/devices/scale-1/command", json.dumps(command))

# Esperar respuesta
import time
time.sleep(2)
client.loop_stop()
```

## Desarrollo

### Estructura del proyecto

```
scale-telemetry/
├── src/
│   └── scale_telemetry/
│       ├── __init__.py          # Exportaciones del paquete
│       ├── config.py            # Configuración y parámetros
│       ├── serial_reader.py     # Lector de báscula serial
│       ├── mqtt_client.py       # Cliente MQTT
│       └── main.py              # Servicio principal
├── tests/                       # Tests unitarios
├── pyproject.toml              # Configuración del proyecto
├── config.env.example          # Ejemplo de configuración
└── README.md                   # Este archivo
```

### Ejecutar tests

```bash
pytest tests/
```

## Logs

El servicio genera logs en:
- **Consola**: Salida estándar
- **Archivo**: `scale_telemetry.log` en el directorio de ejecución

## Solución de problemas

### Error al conectar al puerto serial

```
Error al conectar con la báscula: [Errno 2] No such file or directory: '/dev/ttyUSB0'
```

**Solución**: Verifica que el puerto serial esté correcto. En Linux puedes listar los puertos con:
```bash
ls /dev/tty*
```

En macOS:
```bash
ls /dev/cu.*
```

### Error al conectar al broker MQTT

```
Error al conectar al broker MQTT, código: 1
```

**Solución**: Verifica que el broker MQTT esté corriendo y accesible. Prueba la conexión con:
```bash
mosquitto_pub -h <broker> -t test -m "hello"
```

### La báscula no responde

**Solución**: Verifica:
1. Que la báscula esté encendida
2. Que el cable esté bien conectado
3. Que el baudrate sea el correcto (consulta el manual de la báscula)
4. Los permisos del puerto serial: `sudo chmod 666 /dev/ttyUSB0`

## Licencia

MIT

## Autor

Luis Chavez <lchavezpozo@gmail.com>

