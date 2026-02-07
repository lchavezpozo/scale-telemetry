# 🚀 Inicio Rápido

Esta guía te llevará de cero a tener el sistema funcionando en menos de 5 minutos.

## Opción 1: Docker (Más Fácil) 🐳

### Paso 1: Clonar el repositorio

```bash
git clone <repository-url>
cd scale-telemetry
```

### Paso 2: Ejecutar el script automático

```bash
chmod +x docker-run.sh
./docker-run.sh
```

El script te guiará en la configuración. ¡Eso es todo! 🎉

### Paso 3: Probar que funciona

```bash
# Suscribirse a respuestas
make mqtt-subscribe

# En otra terminal, enviar comando
make mqtt-test
```

## Opción 2: Usando Make (Recomendado)

Si ya tienes Docker instalado:

```bash
# Setup inicial (solo la primera vez)
make setup

# Edita .env con tu puerto serial
nano .env

# Iniciar servicios
make up

# Ver logs
make logs

# Probar
make mqtt-test
```

## Opción 3: Manual con Docker Compose

```bash
# Crear configuración
cp docker.env.example .env
nano .env

# Crear directorios
mkdir -p docker/mosquitto/{data,log} logs

# Iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f
```

## Opción 4: Instalación Local (Sin Docker)

### Paso 1: Instalar

```bash
pip install -e .
```

### Paso 2: Configurar

```bash
export MQTT_BROKER=localhost  # O la IP de tu broker EMQX
export SERIAL_PORT=/dev/ttyUSB0  # Ajusta según tu sistema
```

### Paso 3: Verificar que EMQX esté corriendo

```bash
# Si no tienes EMQX, puedes instalarlo con Docker:
docker run -d --name emqx \
  -p 1883:1883 -p 18083:18083 \
  emqx/emqx:latest

# Dashboard: http://localhost:18083
# User: admin, Password: public (cambiar en producción)
```

### Paso 4: Ejecutar el servicio

```bash
scale-telemetry
```

> 💡 **Nota**: Si ya tienes EMQX corriendo, consulta [EMQX.md](EMQX.md) para configurar la conexión correctamente

## 🧪 Probar sin Hardware Real

### Método 1: Con socat (Recomendado) 🐳

**Terminal 1: Simulador con socat**
```bash
sudo examples/socat_scale_simulator.sh
# Crea /tmp/ttyV0 automáticamente
```

**Terminal 2: Servicio Docker (ya configurado)**
```bash
docker-compose up
# Ya está configurado para usar /tmp/ttyV0
```

**Terminal 3: Probar**
```bash
make mqtt-test
# o usa EMQX Dashboard
```

### Método 2: Con PTY de Python (Local)

**Terminal 1: Simulador PTY**
```bash
python examples/scale_simulator.py
# Copia el puerto que muestra (ej: /dev/ttys001)
```

**Terminal 2: Servicio local**
```bash
export SERIAL_PORT=/dev/ttys001  # Puerto del simulador
scale-telemetry
```

**Terminal 3: Cliente de prueba**
```bash
python examples/mqtt_test_client.py
```

¡Deberías ver el peso en tiempo real! 🎉

> 💡 Ver [examples/SOCAT_GUIDE.md](examples/SOCAT_GUIDE.md) para más detalles sobre socat

## 📋 Comandos Útiles

Con Make (Docker):

```bash
make help              # Ver todos los comandos
make up                # Iniciar servicios
make down              # Detener servicios
make logs              # Ver logs
make restart           # Reiniciar
make mqtt-test         # Enviar comando de prueba
make mqtt-subscribe    # Ver respuestas
make status            # Ver estado
make simulator         # Iniciar simulador con socat
make check-ports       # Listar puertos seriales
```

## 🐛 Problemas Comunes

### No encuentra el puerto serial

```bash
# Ver puertos disponibles
make check-ports

# O manualmente:
# Linux
ls /dev/ttyUSB* /dev/ttyACM*

# macOS
ls /dev/cu.*
```

### Error de permisos en Linux

```bash
# Dar permisos al puerto
sudo chmod 666 /dev/ttyUSB0

# O agregar usuario al grupo dialout (permanente)
sudo usermod -a -G dialout $USER
# Luego cierra sesión e inicia de nuevo
```

### El contenedor no inicia

```bash
# Ver logs detallados
docker-compose logs scale-telemetry

# Verificar configuración
cat .env

# Reiniciar desde cero
make docker-clean
make setup
make up
```

### MQTT no responde

```bash
# Verificar que mosquitto esté corriendo
docker-compose ps

# Ver logs de mosquitto
make docker-logs-mqtt

# Reiniciar mosquitto
docker-compose restart mosquitto
```

## 📖 Más Información

- [README.md](README.md) - Documentación completa
- [DOCKER.md](DOCKER.md) - Guía detallada de Docker
- [examples/README.md](examples/README.md) - Ejemplos de uso
- `make help` - Lista de comandos Make

## 🆘 ¿Necesitas Ayuda?

1. Verifica los logs: `make logs`
2. Revisa la configuración: `cat .env`
3. Consulta DOCKER.md para troubleshooting avanzado
4. Revisa los issues en GitHub

¡Disfruta! 🚀

