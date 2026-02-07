#!/bin/bash
# Script de inicio rápido para Docker

set -e

echo "=== Scale Telemetry - Docker Setup ==="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker no está instalado${NC}"
    echo "Instala Docker desde: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose no está instalado${NC}"
    echo "Instala Docker Compose desde: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker encontrado${NC}"

# Crear directorios necesarios
echo ""
echo "📁 Creando directorios..."
mkdir -p docker/mosquitto/data
mkdir -p docker/mosquitto/log
mkdir -p logs

# Verificar archivo .env
if [ ! -f .env ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Archivo .env no encontrado${NC}"
    echo "Creando desde docker.env.example..."
    cp docker.env.example .env
    echo -e "${GREEN}✅ Archivo .env creado${NC}"
    echo ""
    echo "Por favor, edita .env y configura:"
    echo "  - SERIAL_PORT (tu puerto serial)"
    echo "  - Otras variables según necesites"
    echo ""
    read -p "¿Deseas editar .env ahora? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    fi
fi

# Listar puertos seriales disponibles
echo ""
echo "🔌 Puertos seriales disponibles:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    ls /dev/cu.* 2>/dev/null || echo "  No se encontraron puertos"
else
    # Linux
    ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "  No se encontraron puertos"
fi

echo ""
echo "📝 Verifica que el SERIAL_PORT en .env coincida con uno de los puertos de arriba"
echo ""

# Verificar configuración en docker-compose.yml
echo "⚠️  IMPORTANTE: Asegúrate de descomentar la línea 'devices:' en docker-compose.yml"
echo "   para mapear tu puerto serial al contenedor"
echo ""

read -p "¿Continuar con el inicio? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelado por el usuario"
    exit 0
fi

# Construir y ejecutar
echo ""
echo "🏗️  Construyendo contenedores..."
docker-compose build

echo ""
echo "🚀 Iniciando servicios..."
docker-compose up -d

echo ""
echo -e "${GREEN}✅ Servicios iniciados correctamente${NC}"
echo ""
echo "📊 Estado de los contenedores:"
docker-compose ps

echo ""
echo "📋 Comandos útiles:"
echo "  Ver logs:              docker-compose logs -f"
echo "  Detener servicios:     docker-compose down"
echo "  Reiniciar servicio:    docker-compose restart scale-telemetry"
echo "  Probar MQTT:           make mqtt-test  (o usa el Dashboard de EMQX)"
echo "  Ver comandos:          make help"
echo ""
echo "📖 Para más información:"
echo "  - DOCKER.md - Guía completa de Docker"
echo "  - EMQX.md - Configuración con EMQX"
echo ""
echo -e "${YELLOW}⚠️  Importante: Asegúrate de que EMQX esté corriendo y accesible${NC}"
echo -e "${YELLOW}   Revisa EMQX.md para configurar la conexión correctamente${NC}"
echo ""
echo -e "${GREEN}🎉 ¡Listo! El sistema está corriendo${NC}"

