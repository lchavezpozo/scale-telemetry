# Cambios para usar EMQX en lugar de Mosquitto

Este documento resume los cambios realizados para configurar el proyecto para usar EMQX en lugar de Mosquitto incluido.

## 🔄 Cambios Realizados

### 1. Docker Compose (`docker-compose.yml`)
- ✅ **Eliminado**: Servicio de Mosquitto
- ✅ **Modificado**: Variable `MQTT_BROKER` ahora es configurable (por defecto: `localhost`)
- ✅ **Eliminado**: Dependencia `depends_on: mosquitto`
- ✅ **Agregado**: Comentarios para usar `network_mode: host` si es necesario
- ✅ **Eliminado**: Volúmenes de Mosquitto

### 2. Dockerfile
- ✅ **Modificado**: `MQTT_BROKER` por defecto cambiado de `mosquitto` a `localhost`

### 3. Archivo de Configuración (`docker.env.example`)
- ✅ **Agregado**: Comentarios detallados para configurar EMQX
- ✅ **Agregado**: Instrucciones según diferentes escenarios (host, contenedor, remoto)
- ✅ **Explicado**: Cómo usar `host.docker.internal` o IPs específicas

### 4. Nueva Documentación
- ✅ **Creado**: `EMQX.md` - Guía completa de configuración con EMQX
  - Escenarios de conexión
  - Configuración de autenticación
  - ACL y permisos
  - Solución de problemas
  - Configuración avanzada

### 5. Actualizaciones de Documentación
- ✅ `README.md`: Agregado enlace a guía EMQX
- ✅ `QUICKSTART.md`: Actualizado para mencionar EMQX
- ✅ `docker-run.sh`: Agregado recordatorio sobre EMQX

### 6. Makefile
- ✅ **Actualizado**: Comandos `mqtt-test` y `mqtt-subscribe` para funcionar sin contenedor Mosquitto
- ✅ **Modificado**: `docker-logs-mqtt` y `docker-shell-mqtt` con notas sobre EMQX externo
- ✅ **Limpiado**: `docker-clean` ya no intenta limpiar directorios de Mosquitto

### 7. Archivos Eliminados
- ✅ `docker/mosquitto/config/mosquitto.conf`
- ✅ `docker/README.md` (específico de Mosquitto)

## 📋 Configuración Requerida

### Paso 1: Crear archivo `.env`

```bash
cp docker.env.example .env
```

### Paso 2: Editar `.env` según tu escenario

#### Escenario A: EMQX en el host (localhost)

```bash
MQTT_BROKER=localhost  # O host.docker.internal en macOS/Windows
MQTT_PORT=1883
MQTT_USERNAME=tu-usuario
MQTT_PASSWORD=tu-contraseña
DEVICE_ID=scale-1
SERIAL_PORT=/dev/ttyUSB0
```

#### Escenario B: EMQX en otro contenedor Docker

```bash
MQTT_BROKER=nombre_contenedor_emqx
MQTT_PORT=1883
# ... resto de configuración
```

#### Escenario C: EMQX en servidor remoto

```bash
MQTT_BROKER=mqtt.tu-servidor.com
MQTT_PORT=1883
# ... resto de configuración
```

### Paso 3: (Opcional) Configurar network_mode en docker-compose.yml

Si EMQX está en localhost y tienes problemas de conexión, edita `docker-compose.yml`:

```yaml
scale-telemetry:
  network_mode: "host"
  # Comenta la sección networks:
  # networks:
  #   - scale-network
```

**Nota**: `network_mode: host` solo funciona en Linux.

### Paso 4: Configurar puerto serial

Edita `docker-compose.yml` y descomenta la línea del dispositivo serial:

```yaml
devices:
  - /dev/ttyUSB0:/dev/ttyUSB0  # Ajusta según tu puerto
```

### Paso 5: Iniciar el servicio

```bash
docker-compose up -d
```

## 🔍 Verificar Conexión

### Ver logs

```bash
docker-compose logs -f scale-telemetry
```

Deberías ver:
```
Conectado al broker MQTT en <tu-broker>:1883
Suscrito a: pesanet/devices/scale-1/command
```

### Probar desde EMQX Dashboard

1. Abre: http://localhost:18083 (o tu servidor EMQX)
2. Login: admin / public (por defecto)
3. Ve a: **Tools** → **WebSocket Client**
4. Conecta con tus credenciales
5. Suscríbete a: `pesanet/devices/scale-1/response`
6. Publica en: `pesanet/devices/scale-1/command`
   ```json
   {"command": "get_weight"}
   ```

## 🔒 Configurar Autenticación en EMQX

### Dashboard Web

1. Ve a **Authentication** → **Password-Based**
2. Crea usuario:
   - Username: `scale-user`
   - Password: tu contraseña
3. Ve a **Authorization** → **Rules**
4. Agrega permisos:
   - Allow `subscribe` to `pesanet/devices/+/command`
   - Allow `publish` to `pesanet/devices/+/response`

## 📚 Documentación Adicional

- **[EMQX.md](EMQX.md)** - Guía completa de configuración con EMQX
- **[DOCKER.md](DOCKER.md)** - Guía completa de Docker
- **[QUICKSTART.md](QUICKSTART.md)** - Inicio rápido
- **[README.md](README.md)** - Documentación principal

## ✅ Checklist de Migración

- [ ] EMQX está instalado y corriendo
- [ ] Archivo `.env` creado y configurado
- [ ] Usuario y contraseña configurados en EMQX
- [ ] ACL/permisos configurados en EMQX
- [ ] Puerto serial mapeado en `docker-compose.yml`
- [ ] Servicio inicia sin errores
- [ ] Se conecta a EMQX correctamente
- [ ] Recibe comandos y responde

## 🆘 Problemas Comunes

### "Connection refused"
→ Verifica que EMQX esté corriendo
→ Usa `host.docker.internal` en macOS/Windows
→ Usa `172.17.0.1` en Linux
→ O configura `network_mode: host`

### "Authentication failed"
→ Verifica usuario/contraseña en `.env`
→ Confirma que el usuario existe en EMQX Dashboard

### No recibe mensajes
→ Verifica permisos ACL en EMQX
→ Confirma los tópicos en Dashboard

## 🎯 Resultado Final

Ahora tienes:
- ✅ Servicio de telemetría en Docker
- ✅ Conectado a tu EMQX existente
- ✅ Sin dependencias de Mosquitto
- ✅ Configuración flexible y documentada
- ✅ Fácil de escalar con múltiples básculas

¡Todo listo para producción! 🚀

