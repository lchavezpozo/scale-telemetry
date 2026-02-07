# Ejemplos de Uso

Esta carpeta contiene scripts de ejemplo para probar el sistema de telemetría.

## Scripts disponibles

### 1. Simulador con socat (`socat_scale_simulator.sh`) ⭐ **RECOMENDADO**

Script que usa `socat` para crear un puerto serial virtual y simular una báscula.

**Ventajas:**
- ✅ Más realista (usa dispositivos de carácter reales)
- ✅ Compatible con Docker
- ✅ Funciona en Linux y macOS
- ✅ Limpieza automática

**Uso:**
```bash
chmod +x examples/socat_scale_simulator.sh
sudo examples/socat_scale_simulator.sh
```

Ver [SOCAT_GUIDE.md](SOCAT_GUIDE.md) para más detalles.

### 2. Simulador de Báscula PTY (`scale_simulator.py`)

Simula una báscula usando PTY (pseudo-terminal) de Python.

**Uso:**

```bash
python examples/scale_simulator.py
```

El script creará un puerto serial virtual (por ejemplo `/dev/ttys001`) y mostrará pesos aleatorios cada segundo.

**Configurar el servicio para usar el simulador:**

```bash
# En una terminal, ejecuta el simulador y copia el puerto virtual
python examples/scale_simulator.py

# En otra terminal, configura el puerto y ejecuta el servicio
export SERIAL_PORT=/dev/ttys001  # Usa el puerto que mostró el simulador
scale-telemetry
```

### 2. Cliente de Prueba MQTT (`mqtt_test_client.py`)

Cliente que envía comandos MQTT y muestra las respuestas.

**Uso básico:**

```bash
python examples/mqtt_test_client.py
```

**Con opciones:**

```bash
# Especificar broker y puerto
python examples/mqtt_test_client.py --broker mqtt.example.com --port 1883

# Especificar ID de dispositivo
python examples/mqtt_test_client.py --device-id scale-2
```

**Ayuda:**

```bash
python examples/mqtt_test_client.py --help
```

## Flujo de prueba completo

### 1. Instalar mosquitto (broker MQTT)

**En macOS:**
```bash
brew install mosquitto
brew services start mosquitto
```

**En Ubuntu/Debian:**
```bash
sudo apt-get install mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

### 2. Ejecutar el simulador de báscula

```bash
# Terminal 1: Simulador
python examples/scale_simulator.py
# Anota el puerto serial virtual que muestra (ej: /dev/ttys001)
```

### 3. Ejecutar el servicio de telemetría

```bash
# Terminal 2: Servicio
export SERIAL_PORT=/dev/ttys001  # Usa el puerto del paso anterior
scale-telemetry
```

### 4. Enviar comandos de prueba

```bash
# Terminal 3: Cliente de prueba
python examples/mqtt_test_client.py
```

Deberías ver:
- En Terminal 1: Los pesos que simula la báscula
- En Terminal 2: Logs del servicio procesando comandos
- En Terminal 3: La respuesta con el peso

## Pruebas manuales con mosquitto

También puedes usar las herramientas de mosquitto directamente:

### Suscribirse a respuestas:

```bash
mosquitto_sub -h localhost -t "pesanet/devices/scale-1/response" -v
```

### Enviar comandos:

```bash
# Comando get_weight
mosquitto_pub -h localhost -t "pesanet/devices/scale-1/command" \
  -m '{"command":"get_weight"}'

# Comando inválido (para probar manejo de errores)
mosquitto_pub -h localhost -t "pesanet/devices/scale-1/command" \
  -m '{"command":"invalid"}'

# JSON mal formado (para probar manejo de errores)
mosquitto_pub -h localhost -t "pesanet/devices/scale-1/command" \
  -m 'not a json'
```

## Solución de problemas

### El simulador no crea el puerto serial

**Solución**: El simulador usa PTY (pseudo-terminal), que está disponible en Unix/Linux/macOS. En Windows, considera usar `com0com` o WSL.

### Error "Address already in use" en MQTT

**Solución**: Otro proceso está usando el puerto 1883. Verifica:

```bash
# macOS/Linux
lsof -i :1883

# Detener mosquitto si está corriendo
brew services stop mosquitto  # macOS
sudo systemctl stop mosquitto  # Linux
```

### El cliente de prueba no recibe respuestas

**Solución**: Verifica que:
1. El broker MQTT esté corriendo
2. El servicio de telemetría esté corriendo
3. El simulador de báscula esté enviando datos
4. Los tópicos coincidan (mismo device-id)

