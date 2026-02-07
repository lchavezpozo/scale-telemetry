# 🛠️ Setup de Desarrollo

Esta guía te ayuda a configurar el ambiente de desarrollo con simulador incluido.

## Opción 1: Todo en Docker (Más Fácil) 🐳

Usa `docker-compose.dev.yml` que incluye el simulador de báscula:

### Iniciar todo
```bash
docker-compose -f docker-compose.dev.yml up --build
```

Esto inicia:
- ✅ Simulador de báscula (con socat)
- ✅ Servicio de telemetría
- ✅ Todo configurado automáticamente

### Detener todo
```bash
docker-compose -f docker-compose.dev.yml down
```

### Ver logs
```bash
# Todos los servicios
docker-compose -f docker-compose.dev.yml logs -f

# Solo telemetría
docker-compose -f docker-compose.dev.yml logs -f scale-telemetry

# Solo simulador
docker-compose -f docker-compose.dev.yml logs -f scale-simulator
```

## Opción 2: Simulador Manual (Más Control) 🎮

### Terminal 1: Simulador
```bash
# IMPORTANTE: Iniciar PRIMERO, antes que Docker
sudo examples/socat_scale_simulator.sh
```

Espera a ver:
```
✅ Puertos virtuales creados correctamente
📍 Puerto para el servicio:   /tmp/ttyV0
⚖️ Iniciando simulador de báscula...
[10:30:15] Enviado: 45.3 kg
```

### Terminal 2: Verificar enlaces
```bash
ls -la /tmp/ttyV0
# Debe mostrar: lrwxr-xr-x ... /tmp/ttyV0 -> /dev/pts/X
# NO debe ser un directorio
```

### Terminal 3: Docker
```bash
# Solo DESPUÉS de que socat esté corriendo
docker-compose up --build
```

## Opción 3: Desarrollo Local (Sin Docker) 💻

### Terminal 1: Simulador
```bash
sudo examples/socat_scale_simulator.sh
```

### Terminal 2: Servicio local
```bash
# Instalar dependencias
pip install -e .

# Configurar
export MQTT_BROKER=localhost
export MQTT_USERNAME=admin
export MQTT_PASSWORD=5631699Luis
export SERIAL_PORT=/tmp/ttyV0

# Ejecutar
python -m scale_telemetry.main
```

### Terminal 3: Cliente de prueba
```bash
python examples/mqtt_test_client.py
```

## 🧪 Probar el Sistema

### Método 1: Con mosquitto_pub/sub

**Terminal A: Suscribirse a respuestas**
```bash
mosquitto_sub -h localhost -u admin -P 5631699Luis \
  -t "pesanet/devices/scale-1/response" -v
```

**Terminal B: Enviar comando**
```bash
mosquitto_pub -h localhost -u admin -P 5631699Luis \
  -t "pesanet/devices/scale-1/command" \
  -m '{"command":"get_weight"}'
```

### Método 2: Con EMQX Dashboard

1. Abre: http://localhost:18083
2. Login: admin / public
3. Ve a: **Tools** → **WebSocket Client**
4. Subscribe: `pesanet/devices/scale-1/response`
5. Publish to: `pesanet/devices/scale-1/command`
   ```json
   {"command":"get_weight"}
   ```

### Método 3: Con script de prueba
```bash
python examples/mqtt_test_client.py
```

## 🐛 Solución de Problemas

### Error: "Is a directory: '/tmp/ttyV0'"

**Causa**: Docker inició antes que socat.

**Solución**:
```bash
# 1. Detener todo
docker-compose down
sudo pkill socat

# 2. Limpiar
sudo rm -rf /tmp/ttyV0 /tmp/ttyV1

# 3. Iniciar en orden correcto
# Terminal 1:
sudo examples/socat_scale_simulator.sh

# Terminal 2 (esperar a que socat esté corriendo):
docker-compose up
```

### Error: "Permission denied" en /tmp/ttyV0

**Solución**:
```bash
sudo chmod 666 /tmp/ttyV0 /tmp/ttyV1
```

### El servicio no lee datos del puerto

**Verificar que socat funciona**:
```bash
# Terminal 1: Monitorear
cat /tmp/ttyV0

# Terminal 2: Enviar prueba
echo "42.5 kg" | sudo tee /tmp/ttyV1
```

Si ves "42.5 kg" en Terminal 1, socat funciona ✅

**Verificar dentro del contenedor**:
```bash
# Ver el puerto dentro del contenedor
docker-compose exec scale-telemetry ls -la /tmp/ttyV0

# Leer del puerto dentro del contenedor
docker-compose exec scale-telemetry cat /tmp/ttyV0
```

### El contenedor no se conecta a EMQX

**Verificar red**:
```bash
# Desde el contenedor, hacer ping a EMQX
docker-compose exec scale-telemetry ping -c 3 localhost

# Si no funciona, usa network_mode: host
# Edita docker-compose.yml y descomenta:
# network_mode: "host"
```

## 📊 Comandos Útiles

### Docker
```bash
# Build desde cero
docker-compose build --no-cache

# Ver logs en tiempo real
docker-compose logs -f

# Entrar al contenedor
docker-compose exec scale-telemetry bash

# Ver variables de entorno
docker-compose exec scale-telemetry env | grep SERIAL

# Reiniciar solo un servicio
docker-compose restart scale-telemetry

# Limpiar todo
docker-compose down -v
docker system prune -a
```

### socat
```bash
# Ver procesos socat
ps aux | grep socat

# Detener socat
sudo pkill socat

# Verificar puertos
ls -la /tmp/ttyV*

# Limpiar puertos
sudo rm -f /tmp/ttyV0 /tmp/ttyV1
```

### MQTT
```bash
# Suscribirse a todos los tópicos
mosquitto_sub -h localhost -u admin -P 5631699Luis -t "#" -v

# Ver tópicos de sistema EMQX
mosquitto_sub -h localhost -u admin -P 5631699Luis -t "\$SYS/#"

# Publicar comando
mosquitto_pub -h localhost -u admin -P 5631699Luis \
  -t "pesanet/devices/scale-1/command" \
  -m '{"command":"get_weight"}'
```

## 🎯 Checklist de Desarrollo

- [ ] EMQX está corriendo y accesible
- [ ] socat instalado (`brew install socat`)
- [ ] Simulador iniciado y enviando pesos
- [ ] Puerto `/tmp/ttyV0` existe y es un enlace simbólico
- [ ] Docker Compose construido (`docker-compose build`)
- [ ] Servicio iniciado sin errores
- [ ] Se conecta a EMQX (ver logs)
- [ ] Lee datos del puerto serial (ver logs)
- [ ] Responde a comandos MQTT

## 🚀 Recomendaciones

### Para desarrollo rápido:
```bash
# Usa docker-compose.dev.yml (todo incluido)
docker-compose -f docker-compose.dev.yml up
```

### Para debug:
```bash
# Usa simulador manual en una terminal
sudo examples/socat_scale_simulator.sh

# Y el servicio local en otra
python -m scale_telemetry.main
```

### Para producción:
```bash
# Usa docker-compose.yml con hardware real
# Configura devices en docker-compose.yml
docker-compose up -d
```

¿Preguntas? Revisa los logs:
```bash
docker-compose logs -f scale-telemetry
```

¡Feliz desarrollo! 🎉

