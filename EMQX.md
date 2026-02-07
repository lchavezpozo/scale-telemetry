# 🔌 Configuración con EMQX

Esta guía te ayudará a conectar el servicio de telemetría con tu broker EMQX existente.

## Escenarios de Conexión

### Escenario 1: EMQX en el Host (Recomendado)

Si EMQX está corriendo directamente en tu máquina (fuera de Docker):

#### Opción A: Usar `network_mode: host`

Edita `docker-compose.yml` y descomenta la línea `network_mode: "host"`:

```yaml
scale-telemetry:
  # ... otras configuraciones ...
  network_mode: "host"
  # Comenta la sección de networks:
  # networks:
  #   - scale-network
```

En tu archivo `.env`:
```bash
MQTT_BROKER=localhost
MQTT_PORT=1883
```

**Ventajas:**
- Simple y directo
- El contenedor comparte la red del host
- Acceso directo a localhost

**Desventajas:**
- Solo funciona en Linux
- No funciona en macOS/Windows con Docker Desktop

#### Opción B: Usar `host.docker.internal`

Mantén la configuración de red bridge y en `.env`:

```bash
# macOS / Windows
MQTT_BROKER=host.docker.internal
MQTT_PORT=1883

# Linux (usa la IP del gateway de Docker)
MQTT_BROKER=172.17.0.1
MQTT_PORT=1883
```

### Escenario 2: EMQX en otro Contenedor

Si EMQX también está en Docker, necesitas conectar ambos contenedores.

#### Opción A: Red externa existente

Si EMQX ya está en una red Docker:

```yaml
# docker-compose.yml
networks:
  scale-network:
    external: true
    name: nombre-de-tu-red-emqx
```

En `.env`:
```bash
MQTT_BROKER=nombre_contenedor_emqx
MQTT_PORT=1883
```

#### Opción B: Crear red compartida

```bash
# Crear red compartida
docker network create mqtt-network

# Conectar EMQX a la red (si no lo está ya)
docker network connect mqtt-network nombre_contenedor_emqx

# En docker-compose.yml
networks:
  scale-network:
    external: true
    name: mqtt-network
```

En `.env`:
```bash
MQTT_BROKER=nombre_contenedor_emqx
MQTT_PORT=1883
```

### Escenario 3: EMQX en Servidor Remoto

Si EMQX está en otro servidor:

En `.env`:
```bash
MQTT_BROKER=mqtt.tu-servidor.com
MQTT_PORT=1883
MQTT_USERNAME=tu-usuario
MQTT_PASSWORD=tu-contraseña
```

## 🔒 Autenticación con EMQX

EMQX generalmente requiere autenticación. Configura las credenciales en `.env`:

```bash
MQTT_USERNAME=scale-user
MQTT_PASSWORD=tu-contraseña-segura
```

### Crear Usuario en EMQX

Si tienes acceso al dashboard de EMQX:

1. Abre el Dashboard: http://localhost:18083 (por defecto)
2. Ve a **Authentication** → **Password-Based**
3. Crea un nuevo usuario:
   - Username: `scale-user`
   - Password: tu contraseña
   - Assign permisos para los tópicos:
     - Subscribe: `pesanet/devices/+/command`
     - Publish: `pesanet/devices/+/response`

### ACL (Control de Acceso)

Configura los permisos en EMQX para que el dispositivo solo pueda:

```json
{
  "username": "scale-user",
  "rules": [
    {
      "action": "subscribe",
      "topic": "pesanet/devices/${username}/command",
      "allow": true
    },
    {
      "action": "publish", 
      "topic": "pesanet/devices/${username}/response",
      "allow": true
    }
  ]
}
```

## 🧪 Probar la Conexión

### 1. Verificar que EMQX esté accesible

```bash
# Desde el host
mosquitto_pub -h localhost -p 1883 -t "test" -m "hello"

# O con EMQX CLI
emqx_ctl status
```

### 2. Iniciar el servicio

```bash
docker-compose up -d
```

### 3. Ver logs para verificar conexión

```bash
docker-compose logs -f scale-telemetry
```

Deberías ver:
```
Conectado al broker MQTT en <tu-broker>:1883
Suscrito a: pesanet/devices/scale-1/command
```

### 4. Probar desde EMQX Dashboard

1. Abre el Dashboard de EMQX
2. Ve a **WebSocket Client** o **MQTT X**
3. Suscríbete a: `pesanet/devices/scale-1/response`
4. Publica en: `pesanet/devices/scale-1/command`
   ```json
   {"command": "get_weight"}
   ```

## 🐛 Solución de Problemas

### Error: "Connection refused"

**Problema**: El contenedor no puede conectarse a EMQX.

**Soluciones**:

1. **Verifica que EMQX esté corriendo**:
```bash
# Si EMQX está en Docker
docker ps | grep emqx

# Si EMQX está en el host
ps aux | grep emqx
# o
systemctl status emqx
```

2. **Verifica la dirección del broker**:
```bash
# Desde dentro del contenedor
docker-compose exec scale-telemetry ping -c 3 host.docker.internal

# O prueba conectar con telnet
docker-compose exec scale-telemetry telnet $MQTT_BROKER $MQTT_PORT
```

3. **Verifica el firewall**:
```bash
# Linux - permitir puerto 1883
sudo ufw allow 1883/tcp
```

### Error: "Authentication failed"

**Problema**: Las credenciales no son correctas.

**Solución**:

1. Verifica las credenciales en `.env`
2. Verifica que el usuario exista en EMQX Dashboard
3. Prueba conectar manualmente:
```bash
mosquitto_sub -h localhost -p 1883 \
  -u "tu-usuario" -P "tu-contraseña" \
  -t "test"
```

### El contenedor se conecta pero no recibe mensajes

**Problema**: Permisos ACL en EMQX.

**Solución**:

1. Verifica los permisos en EMQX Dashboard
2. Asegúrate que el usuario tiene permiso para:
   - Subscribe a `pesanet/devices/scale-1/command`
   - Publish a `pesanet/devices/scale-1/response`
3. Revisa los logs de EMQX:
```bash
docker logs nombre_contenedor_emqx
```

### No puede conectarse desde Docker en Linux

**Problema**: Firewall del host bloqueando conexiones desde Docker.

**Solución**:

Usa `network_mode: host` en `docker-compose.yml`:
```yaml
scale-telemetry:
  network_mode: "host"
  # Comenta: networks: ...
```

O ajusta iptables:
```bash
sudo iptables -A INPUT -i docker0 -j ACCEPT
```

## 📊 Configuración Avanzada

### TLS/SSL con EMQX

Si tu EMQX usa TLS:

1. Cambia el puerto en `.env`:
```bash
MQTT_PORT=8883
```

2. Modifica `mqtt_client.py` para usar SSL (puedes agregar soporte si lo necesitas).

### Múltiples Básculas con EMQX

Para conectar varias básculas:

```bash
# Terminal 1 - Báscula 1
docker-compose up scale-telemetry

# Terminal 2 - Báscula 2
docker-compose -f docker-compose.scale2.yml up
```

Con diferentes `DEVICE_ID` en cada archivo.

### Monitoreo en EMQX

Usa el Dashboard de EMQX para monitorear:
- Conexiones activas
- Mensajes publicados/recibidos
- Tráfico por tópico
- Métricas de rendimiento

## 🔗 Enlaces Útiles

- [EMQX Documentation](https://www.emqx.io/docs/en/v5.0/)
- [EMQX Dashboard](http://localhost:18083) (por defecto)
- [MQTT X Client](https://mqttx.app/) (cliente GUI para testing)

## ✅ Checklist de Configuración

- [ ] EMQX está corriendo y accesible
- [ ] Usuario y contraseña configurados en EMQX
- [ ] Permisos ACL configurados
- [ ] Variables en `.env` configuradas correctamente
- [ ] Red Docker configurada (host o bridge)
- [ ] Puerto serial mapeado en `docker-compose.yml`
- [ ] Servicio inicia sin errores (`docker-compose logs`)
- [ ] Se conecta a EMQX (ver logs)
- [ ] Recibe comandos y responde correctamente

¿Necesitas ayuda con alguna configuración específica? 🚀

