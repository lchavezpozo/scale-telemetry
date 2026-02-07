# 🐳 Guía Docker

Esta guía te ayudará a ejecutar el sistema de telemetría usando Docker.

## 📋 Requisitos

- Docker Engine 20.10+
- Docker Compose V2
- Acceso al puerto serial de la báscula

## 🚀 Inicio Rápido

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd scale-telemetry
```

### 2. Configurar variables de entorno (opcional)

```bash
cp docker.env.example .env
nano .env  # Edita según tus necesidades
```

### 3. Configurar el puerto serial

Edita `docker-compose.yml` y descomenta/ajusta la línea del dispositivo serial:

```yaml
devices:
  - /dev/ttyUSB0:/dev/ttyUSB0  # Linux
  # - /dev/ttyACM0:/dev/ttyACM0  # Arduino en Linux
  # - /dev/cu.usbserial-1420:/dev/ttyUSB0  # macOS
```

### 4. Construir y ejecutar

```bash
docker-compose up --build
```

Para ejecutar en background:

```bash
docker-compose up -d
```

## 📊 Comandos Útiles

### Ver logs

```bash
# Todos los servicios
docker-compose logs -f

# Solo telemetría
docker-compose logs -f scale-telemetry

# Solo MQTT broker
docker-compose logs -f mosquitto
```

### Detener los servicios

```bash
docker-compose down
```

### Reiniciar un servicio específico

```bash
docker-compose restart scale-telemetry
```

### Reconstruir después de cambios

```bash
docker-compose up --build -d
```

### Ver estado de los contenedores

```bash
docker-compose ps
```

### Entrar al contenedor

```bash
# Telemetría
docker-compose exec scale-telemetry bash

# Mosquitto
docker-compose exec mosquitto sh
```

## 🧪 Probar el Sistema

### 1. Verificar que los servicios estén corriendo

```bash
docker-compose ps
```

Deberías ver:
```
NAME                IMAGE                      STATUS
scale-mosquitto     eclipse-mosquitto:2.0      Up
scale-telemetry     scale-telemetry:latest     Up
```

### 2. Suscribirse a las respuestas

```bash
docker-compose exec mosquitto mosquitto_sub \
  -h localhost \
  -t "pesanet/devices/scale-1/response" \
  -v
```

### 3. Enviar un comando (en otra terminal)

```bash
docker-compose exec mosquitto mosquitto_pub \
  -h localhost \
  -t "pesanet/devices/scale-1/command" \
  -m '{"command":"get_weight"}'
```

### 4. Desde el host (si mosquitto está expuesto)

```bash
# Suscribirse
mosquitto_sub -h localhost -t "pesanet/devices/scale-1/response"

# Publicar comando
mosquitto_pub -h localhost \
  -t "pesanet/devices/scale-1/command" \
  -m '{"command":"get_weight"}'
```

## 🔧 Configuración Avanzada

### Variables de Entorno

Puedes configurar el sistema mediante variables de entorno en el archivo `.env`:

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `MQTT_USERNAME` | Usuario MQTT | (vacío) |
| `MQTT_PASSWORD` | Contraseña MQTT | (vacío) |
| `DEVICE_ID` | ID del dispositivo | `scale-1` |
| `SERIAL_PORT` | Puerto serial | `/dev/ttyUSB0` |
| `SERIAL_BAUDRATE` | Velocidad baudios | `9600` |
| `SERIAL_TIMEOUT` | Timeout lectura (seg) | `1.0` |

### Múltiples Básculas

Para ejecutar múltiples instancias con diferentes básculas:

1. Crea archivos docker-compose separados:

```yaml
# docker-compose.scale2.yml
version: '3.8'
services:
  scale-telemetry-2:
    build: .
    environment:
      - DEVICE_ID=scale-2
      - SERIAL_PORT=/dev/ttyUSB1
      - MQTT_BROKER=mosquitto
    devices:
      - /dev/ttyUSB1:/dev/ttyUSB1
    networks:
      - scale-network

networks:
  scale-network:
    external: true
```

2. Ejecuta ambos:

```bash
docker-compose up -d
docker-compose -f docker-compose.scale2.yml up -d
```

### Usar Broker MQTT Externo

Si ya tienes un broker MQTT corriendo:

1. Comenta el servicio `mosquitto` en `docker-compose.yml`

2. Actualiza las variables de entorno:

```yaml
environment:
  - MQTT_BROKER=mqtt.tu-servidor.com
  - MQTT_PORT=1883
  - MQTT_USERNAME=tu-usuario
  - MQTT_PASSWORD=tu-contraseña
```

### Volúmenes Persistentes

Los datos se guardan en:

```
./docker/mosquitto/data/  # Datos MQTT persistentes
./docker/mosquitto/log/   # Logs de Mosquitto
./logs/                   # Logs del servicio
```

## 🐛 Solución de Problemas

### Error: "No such file or directory: '/dev/ttyUSB0'"

**Problema**: El puerto serial no está disponible en el contenedor.

**Soluciones**:

1. Verifica que el dispositivo existe en el host:
```bash
ls -l /dev/tty*
```

2. Ajusta el mapeo de dispositivos en `docker-compose.yml`:
```yaml
devices:
  - /dev/ttyUSB0:/dev/ttyUSB0  # Ajusta según tu puerto
```

3. Si usas macOS, el dispositivo suele ser `/dev/cu.usbserial-*`:
```bash
ls /dev/cu.*
```

4. Da permisos al puerto (Linux):
```bash
sudo chmod 666 /dev/ttyUSB0
```

### Error: "Permission denied" en puerto serial

**Solución 1**: Agrega privilegios al contenedor (menos seguro):
```yaml
privileged: true
```

**Solución 2**: Agrega el usuario al grupo dialout (más seguro):
```bash
# En el host
sudo usermod -a -G dialout $USER
# Cierra sesión y vuelve a iniciar
```

### Error: "Connection refused" al conectar a MQTT

**Problema**: El servicio de telemetría intenta conectarse antes de que Mosquitto esté listo.

**Solución**: El docker-compose ya tiene `depends_on`, pero puedes agregar un healthcheck:

```yaml
mosquitto:
  healthcheck:
    test: ["CMD", "mosquitto_sub", "-t", "$$SYS/#", "-C", "1", "-i", "healthcheck"]
    interval: 10s
    timeout: 5s
    retries: 5

scale-telemetry:
  depends_on:
    mosquitto:
      condition: service_healthy
```

### Ver logs detallados

```bash
# Todos los logs
docker-compose logs --tail=100 -f

# Solo errores
docker-compose logs | grep -i error

# Logs del servicio Python
docker-compose exec scale-telemetry cat /var/log/scale-telemetry/scale_telemetry.log
```

### El contenedor se reinicia constantemente

1. Verifica los logs:
```bash
docker-compose logs scale-telemetry
```

2. Verifica el healthcheck:
```bash
docker inspect scale-telemetry | grep -A 10 Health
```

3. Entra al contenedor para debug:
```bash
docker-compose run --rm scale-telemetry bash
# Dentro del contenedor:
python -m scale_telemetry.main
```

## 🔒 Seguridad en Producción

### 1. Habilitar autenticación MQTT

Edita `docker/mosquitto/config/mosquitto.conf`:

```conf
allow_anonymous false
password_file /mosquitto/config/passwd
```

Crea usuarios:

```bash
docker-compose exec mosquitto mosquitto_passwd -c /mosquitto/config/passwd admin
docker-compose restart mosquitto
```

### 2. Usar secrets de Docker

```yaml
secrets:
  mqtt_password:
    file: ./secrets/mqtt_password.txt

services:
  scale-telemetry:
    secrets:
      - mqtt_password
    environment:
      - MQTT_PASSWORD_FILE=/run/secrets/mqtt_password
```

### 3. Network isolation

```yaml
networks:
  scale-network:
    driver: bridge
    internal: true  # Red interna, sin acceso a internet
```

### 4. Límites de recursos

```yaml
scale-telemetry:
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 256M
      reservations:
        cpus: '0.25'
        memory: 128M
```

## 📈 Monitoreo

### Usar con Portainer

```bash
docker volume create portainer_data

docker run -d \
  -p 9000:9000 \
  --name portainer \
  --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce
```

Accede a http://localhost:9000

### Logs con Loki + Grafana

Puedes agregar logging centralizado editando `docker-compose.yml`:

```yaml
services:
  scale-telemetry:
    logging:
      driver: loki
      options:
        loki-url: "http://localhost:3100/loki/api/v1/push"
```

## 📦 Publicar la Imagen

### Construir para múltiples arquitecturas

```bash
docker buildx create --name multiarch --use
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7 \
  -t tuusuario/scale-telemetry:latest \
  --push .
```

### Publicar en Docker Hub

```bash
docker login
docker tag scale-telemetry:latest tuusuario/scale-telemetry:latest
docker push tuusuario/scale-telemetry:latest
```

## 🎯 Siguiente Pasos

- [ ] Configurar CI/CD para builds automáticos
- [ ] Agregar métricas con Prometheus
- [ ] Implementar dashboard con Grafana
- [ ] Agregar tests de integración con Docker
- [ ] Configurar backup automático de datos

¿Necesitas ayuda con alguno de estos temas? ¡Pregunta! 🚀

