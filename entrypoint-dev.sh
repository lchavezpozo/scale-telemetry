#!/bin/bash
# Entrypoint para desarrollo que convierte el FIFO en un puerto PTY con socat

set -e

echo "=== Scale Telemetry - Development Mode ==="
echo ""
echo "🌐 Información de Red:"
echo "   Hostname: $(hostname)"
echo "   IP Container: $(hostname -i 2>/dev/null || echo 'N/A')"
echo ""
echo "📡 Variables MQTT:"
echo "   MQTT_BROKER: ${MQTT_BROKER}"
echo "   MQTT_PORT: ${MQTT_PORT}"
echo "   MQTT_USERNAME: ${MQTT_USERNAME}"
echo ""

# Verificar que el FIFO existe
if [ ! -p /shared/scale_pipe ]; then
    echo "ERROR: FIFO /shared/scale_pipe no existe"
    exit 1
fi

echo "✅ FIFO encontrado: /shared/scale_pipe"

# Crear puerto PTY desde el FIFO usando socat
echo "🔧 Creando puerto PTY virtual..."
socat -d -d pty,raw,echo=0,link=/tmp/vty0 file:/shared/scale_pipe &
SOCAT_PID=$!

echo "✅ socat PID: $SOCAT_PID"

# Esperar a que se cree el puerto
echo "⏳ Esperando a que se cree /tmp/vty0..."
for i in {1..10}; do
    if [ -e /tmp/vty0 ]; then
        echo "✅ Puerto PTY creado: /tmp/vty0"
        break
    fi
    echo "   Intento $i/10..."
    sleep 1
done

if [ ! -e /tmp/vty0 ]; then
    echo "❌ ERROR: No se pudo crear el puerto PTY"
    kill $SOCAT_PID 2>/dev/null || true
    exit 1
fi

# Dar permisos
chmod 666 /tmp/vty0
ls -la /tmp/vty0

# Función de limpieza
cleanup() {
    echo "🛑 Deteniendo socat..."
    kill $SOCAT_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT EXIT

# Configurar SERIAL_PORT para usar el PTY
export SERIAL_PORT=/tmp/vty0

echo ""
echo "🔍 Probando conectividad a MQTT..."
# Intentar ping (si está disponible)
if command -v ping &> /dev/null; then
    echo "   Ping a ${MQTT_BROKER}:"
    ping -c 2 ${MQTT_BROKER} 2>&1 | head -n 5 || echo "   ⚠️  Ping falló"
else
    echo "   (ping no disponible)"
fi

echo ""
echo "🚀 Iniciando Scale Telemetry Service..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Ejecutar el servicio principal
exec scale-telemetry

