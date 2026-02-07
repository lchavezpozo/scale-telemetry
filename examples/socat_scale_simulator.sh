#!/bin/bash
# Script para simular una báscula usando socat
# Este script crea un puerto serial virtual y envía datos simulados

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Simulador de Báscula con socat ===${NC}\n"

# Parámetros
RANDOM_MODE=false
FIXED_WEIGHT=120

usage() {
    cat <<EOF
Uso: $0 [--random] [--weight PESO]

Opciones:
  --random          Envía pesos aleatorios cada segundo (0-150 kg).
  --weight PESO     Peso fijo en kilogramos cuando no se usa modo aleatorio. Por defecto 120.
  -h, --help        Muestra esta ayuda.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --random)
            RANDOM_MODE=true
            shift
            ;;
        --weight)
            if [[ -z "${2:-}" ]]; then
                echo -e "${RED}❌ Error: --weight requiere un valor${NC}"
                exit 1
            fi
            FIXED_WEIGHT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Opción no reconocida: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Verificar si socat está instalado
if ! command -v socat &> /dev/null; then
    echo -e "${RED}❌ socat no está instalado${NC}"
    echo ""
    echo "Instala socat:"
    echo "  macOS:   brew install socat"
    echo "  Ubuntu:  sudo apt-get install socat"
    echo "  CentOS:  sudo yum install socat"
    exit 1
fi

echo -e "${GREEN}✅ socat encontrado${NC}"

# Puertos virtuales
PTY_VIRTUAL="/tmp/ttyV0"
PTY_SIMULATOR="/tmp/ttyV1"

# Limpiar puertos si existen
echo -e "\n${YELLOW}🧹 Limpiando puertos virtuales anteriores...${NC}"
sudo rm -f "$PTY_VIRTUAL" "$PTY_SIMULATOR" 2>/dev/null || true

# Crear par de puertos virtuales con socat
echo -e "${BLUE}📡 Creando par de puertos virtuales...${NC}"
echo -e "   ${PTY_VIRTUAL} <-> ${PTY_SIMULATOR}"

# Ejecutar socat en background
sudo socat -d -d \
    pty,raw,echo=0,link="$PTY_VIRTUAL" \
    pty,raw,echo=0,link="$PTY_SIMULATOR" &

SOCAT_PID=$!
echo -e "${GREEN}✅ socat ejecutándose (PID: $SOCAT_PID)${NC}"

# Esperar a que se creen los dispositivos
sleep 1

# Verificar que los dispositivos existen
if [ ! -e "$PTY_VIRTUAL" ] || [ ! -e "$PTY_SIMULATOR" ]; then
    echo -e "${RED}❌ Error: Los dispositivos no se crearon correctamente${NC}"
    sudo kill $SOCAT_PID 2>/dev/null || true
    exit 1
fi

# Dar permisos
echo -e "${BLUE}🔑 Configurando permisos...${NC}"
sudo chmod 666 "$PTY_VIRTUAL" "$PTY_SIMULATOR"
echo -e "${GREEN}✅ Permisos configurados${NC}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Puertos virtuales creados correctamente${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "📍 ${BLUE}Puerto para el servicio:${NC}   $PTY_VIRTUAL"
echo -e "📍 ${BLUE}Puerto para el simulador:${NC} $PTY_SIMULATOR"
echo ""
echo -e "${YELLOW}Configura el servicio para usar:${NC}"
echo -e "  export SERIAL_PORT=$PTY_VIRTUAL"
echo -e "  o en docker-compose.yml: - $PTY_VIRTUAL:/dev/ttyUSB0"
echo ""

# Función para limpiar al salir
cleanup() {
    echo -e "\n${YELLOW}🛑 Deteniendo socat...${NC}"
    sudo kill $SOCAT_PID 2>/dev/null || true
    sudo rm -f "$PTY_VIRTUAL" "$PTY_SIMULATOR" 2>/dev/null || true
    echo -e "${GREEN}✅ Limpieza completada${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Iniciar simulador de báscula
echo -e "${BLUE}⚖️  Iniciando simulador de báscula...${NC}"
if $RANDOM_MODE; then
    echo -e "${GREEN}Modo:${NC} ${YELLOW}Pesos aleatorios (0-150 kg)${NC}"
else
    printf "${GREEN}Modo:${NC} ${YELLOW}Peso fijo${NC} %.1f kg\n" "$FIXED_WEIGHT"
fi
echo -e "${YELLOW}Presiona Ctrl+C para detener${NC}\n"

# Simular envío de pesos
contador=0
while true; do
    if $RANDOM_MODE; then
        # Generar peso aleatorio entre 0 y 150 kg con 1 decimal
        peso=$(awk -v min=0 -v max=150 'BEGIN{srand(); printf "%.1f\n", min+rand()*(max-min)}')
    else
        peso=$(awk -v value="$FIXED_WEIGHT" 'BEGIN{printf "%.1f\n", value}')
    fi
    
    # Enviar al puerto virtual
    echo "$peso kg" | sudo tee "$PTY_SIMULATOR" > /dev/null
    
    # Mostrar en pantalla
    timestamp=$(date '+%H:%M:%S')
    echo -e "${GREEN}[$timestamp]${NC} Enviado: ${BLUE}$peso kg${NC}"
    
    # Incrementar contador
    ((contador++))
    
    # Cada 10 envíos, mostrar estadísticas
    if [ $((contador % 10)) -eq 0 ]; then
        echo -e "${YELLOW}━━━ Enviados: $contador mensajes ━━━${NC}"
    fi
    
    # Esperar 1 segundo
    sleep 1
done

