# 🔌 Guía de uso de socat para simular puerto serial

Esta guía te ayuda a usar `socat` para crear un puerto serial virtual y probar el sistema sin hardware real.

## ¿Qué es socat?

`socat` (SOcket CAT) es una herramienta que permite crear pares de puertos virtuales que se comportan como puertos seriales reales.

## Instalación

### macOS
```bash
brew install socat
```

### Ubuntu/Debian
```bash
sudo apt-get install socat
```

### CentOS/RHEL
```bash
sudo yum install socat
```

## Método 1: Usar el Script Automático (Recomendado) 🚀

### Paso 1: Hacer ejecutable el script
```bash
chmod +x examples/socat_scale_simulator.sh
```

### Paso 2: Ejecutar el simulador
```bash
sudo examples/socat_scale_simulator.sh
```

El script:
- ✅ Crea automáticamente `/tmp/ttyV0` y `/tmp/ttyV1`
- ✅ Configura permisos
- ✅ Inicia el simulador de báscula
- ✅ Envía pesos aleatorios cada segundo
- ✅ Limpia todo al salir (Ctrl+C)

### Paso 3: En otra terminal, inicia el servicio

**Con Docker:**
```bash
# El docker-compose.yml ya está configurado para /tmp/ttyV0
docker-compose up
```

**Local:**
```bash
export SERIAL_PORT=/tmp/ttyV0
scale-telemetry
```

### Paso 4: Probar
```bash
# En otra terminal
make mqtt-test
# o usa EMQX Dashboard
```

## Método 2: Manual (Paso a Paso)

### Paso 1: Crear par de puertos virtuales

```bash
sudo socat -d -d \
  pty,raw,echo=0,link=/tmp/ttyV0 \
  pty,raw,echo=0,link=/tmp/ttyV1 &
```

Esto crea dos puertos conectados:
- `/tmp/ttyV0` - Para el servicio de telemetría
- `/tmp/ttyV1` - Para escribir datos simulados

### Paso 2: Verificar que se crearon

```bash
ls -l /tmp/ttyV*
```

Deberías ver:
```
lrwxr-xr-x  1 root  wheel  10 Oct 26 10:00 /tmp/ttyV0 -> /dev/pts/4
lrwxr-xr-x  1 root  wheel  10 Oct 26 10:00 /tmp/ttyV1 -> /dev/pts/5
```

### Paso 3: Dar permisos

```bash
sudo chmod 666 /tmp/ttyV0 /tmp/ttyV1
```

### Paso 4: Enviar datos de prueba

En una terminal:
```bash
# Enviar pesos manualmente
while true; do 
  echo "$(awk 'BEGIN{srand(); printf "%.1f", rand()*150}') kg" | sudo tee /tmp/ttyV1
  sleep 1
done
```

### Paso 5: Iniciar el servicio

En otra terminal:
```bash
# Docker
docker-compose up

# Local
export SERIAL_PORT=/tmp/ttyV0
scale-telemetry
```

## Método 3: Con Docker Compose incluido

Si quieres que el simulador también esté en Docker:

### Crear docker-compose.dev.yml

```yaml
version: '3.8'

services:
  # Simulador de báscula con socat
  scale-simulator:
    image: alpine:latest
    container_name: scale-simulator
    privileged: true
    command: >
      sh -c "
        apk add --no-cache socat &&
        socat -d -d 
          pty,raw,echo=0,link=/tmp/ttyV0 
          pty,raw,echo=0,link=/tmp/ttyV1 &
        sleep 2 &&
        chmod 666 /tmp/ttyV0 /tmp/ttyV1 &&
        while true; do
          echo \"\$$(awk 'BEGIN{srand(); printf \"%.1f\", rand()*150}') kg\" > /tmp/ttyV1
          sleep 1
        done
      "
    volumes:
      - /tmp:/tmp

  # Servicio de telemetría
  scale-telemetry:
    extends:
      file: docker-compose.yml
      service: scale-telemetry
    depends_on:
      - scale-simulator
    volumes:
      - ./logs:/var/log/scale-telemetry
      - /tmp:/tmp
```

### Ejecutar
```bash
docker-compose -f docker-compose.dev.yml up
```

## Solución de Problemas

### Error: "Permission denied" al acceder al puerto

**Solución:**
```bash
sudo chmod 666 /tmp/ttyV0 /tmp/ttyV1
```

### Error: "No such file or directory"

**Problema:** El proceso de socat murió o los enlaces no se crearon.

**Solución:**
```bash
# Matar procesos socat anteriores
sudo pkill socat

# Limpiar enlaces
sudo rm -f /tmp/ttyV0 /tmp/ttyV1

# Crear de nuevo
sudo socat -d -d \
  pty,raw,echo=0,link=/tmp/ttyV0 \
  pty,raw,echo=0,link=/tmp/ttyV1 &
```

### Error: "Device or resource busy"

**Problema:** Otro proceso está usando los puertos.

**Solución:**
```bash
# Ver qué procesos usan los puertos
sudo lsof /tmp/ttyV0 /tmp/ttyV1

# Detener el servicio
docker-compose down

# Matar socat
sudo pkill socat

# Limpiar y reiniciar
sudo rm -f /tmp/ttyV0 /tmp/ttyV1
```

### Docker no puede acceder al puerto

**Problema:** El contenedor no tiene permisos.

**Solución 1:** Usar `privileged: true` (menos seguro)
```yaml
scale-telemetry:
  privileged: true
```

**Solución 2:** Ajustar permisos antes de iniciar
```bash
sudo chmod 666 /tmp/ttyV0
docker-compose up
```

### Los datos no llegan al servicio

**Verificar conexión:**
```bash
# Terminal 1: Monitorear lo que llega a ttyV0
cat /tmp/ttyV0

# Terminal 2: Enviar datos de prueba
echo "42.5 kg" | sudo tee /tmp/ttyV1
```

Si ves "42.5 kg" en Terminal 1, socat funciona correctamente.

### El servicio no parsea el peso

**Verificar el formato:**

El servicio espera que el peso esté en el formato:
- `"45.3 kg"`
- `"45.3"`
- `"Weight: 45.3"`

Verifica los logs:
```bash
docker-compose logs -f scale-telemetry
```

## Comandos Útiles

### Ver procesos socat
```bash
ps aux | grep socat
```

### Detener todos los socat
```bash
sudo pkill socat
```

### Monitorear datos en tiempo real
```bash
# Ver lo que se envía
cat /tmp/ttyV1

# Ver lo que se recibe
cat /tmp/ttyV0
```

### Limpiar todo
```bash
sudo pkill socat
sudo rm -f /tmp/ttyV0 /tmp/ttyV1
```

## Flujo Completo de Prueba

### Terminal 1: Simulador
```bash
sudo examples/socat_scale_simulator.sh
```

### Terminal 2: Servicio
```bash
docker-compose up
```

### Terminal 3: Cliente MQTT
```bash
# Suscribirse a respuestas
make mqtt-subscribe

# En otra terminal, enviar comando
make mqtt-test
```

Deberías ver:
1. Terminal 1: Pesos siendo enviados
2. Terminal 2: Logs del servicio leyendo pesos
3. Terminal 3: Respuesta MQTT con el peso

## Alternativas a socat

### 1. Usando `pty` de Python (sin socat)

```python
import os
import pty
import time
import random

master, slave = pty.openpty()
slave_name = os.ttyname(slave)
print(f"Puerto creado: {slave_name}")

while True:
    peso = random.uniform(0, 150)
    os.write(master, f"{peso:.1f} kg\n".encode())
    time.sleep(1)
```

### 2. Usando simulador Python incluido

```bash
# Usar el simulador PTY de Python incluido
python examples/scale_simulator.py
# Te dirá qué puerto usar
```

## Configuración para Producción

Cuando uses hardware real:

1. Comenta el mapeo de socat en `docker-compose.yml`:
```yaml
devices:
  # - /tmp/ttyV0:/dev/ttyUSB0  # Simulador
  - /dev/ttyUSB0:/dev/ttyUSB0  # Hardware real
```

2. Ajusta el baudrate según tu báscula:
```yaml
environment:
  - SERIAL_BAUDRATE=9600  # o 4800, 19200, etc.
```

## Resumen

- ✅ **Script automático**: `sudo examples/socat_scale_simulator.sh`
- ✅ **Puerto servicio**: `/tmp/ttyV0`
- ✅ **Puerto simulador**: `/tmp/ttyV1`
- ✅ **Limpiar**: `sudo pkill socat && sudo rm -f /tmp/ttyV*`

¿Problemas? Revisa los logs:
```bash
docker-compose logs -f scale-telemetry
```

¡Listo para probar! 🚀

