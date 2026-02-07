"""Punto de entrada principal del sistema de telemetría."""

import logging
import signal
import sys
from typing import Optional

from .config import MQTTConfig, SerialConfig
from .mqtt_client import ScaleMQTTClient
from .serial_reader import ScaleReader

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scale_telemetry.log')
    ]
)

logger = logging.getLogger(__name__)


class ScaleTelemetryService:
    """Servicio principal de telemetría de báscula."""
    
    def __init__(self):
        """Inicializa el servicio."""
        self.mqtt_config = MQTTConfig()
        self.serial_config = SerialConfig()
        self.scale_reader: Optional[ScaleReader] = None
        self.mqtt_client: Optional[ScaleMQTTClient] = None
        self.running = False
    
    def _get_weight(self) -> float:
        """
        Obtiene el peso actual de la báscula.
        
        Returns:
            Peso en kilogramos
        """
        if not self.scale_reader:
            raise RuntimeError("Lector de báscula no inicializado")
        return self.scale_reader.read_weight()
    
    def start(self):
        """Inicia el servicio de telemetría."""
        logger.info("=== Iniciando Scale Telemetry Service ===")
        logger.info(f"Device ID: {self.mqtt_config.device_id}")
        logger.info(f"MQTT Broker: {self.mqtt_config.broker}:{self.mqtt_config.port}")
        logger.info(f"Command Topic: {self.mqtt_config.command_topic}")
        logger.info(f"Response Topic: {self.mqtt_config.response_topic}")
        logger.info(f"Serial Port: {self.serial_config.port}")
        
        try:
            # Inicializar lector de báscula
            self.scale_reader = ScaleReader(self.serial_config)
            self.scale_reader.connect()
            
            # Inicializar cliente MQTT
            self.mqtt_client = ScaleMQTTClient(self.mqtt_config, self._get_weight)
            self.mqtt_client.connect()
            
            # Configurar manejador de señales para cierre graceful
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            self.running = True
            logger.info("Servicio iniciado correctamente. Esperando comandos...")
            
            # Iniciar loop MQTT (bloqueante)
            self.mqtt_client.start()
            
        except KeyboardInterrupt:
            logger.info("Interrupción de teclado recibida")
        except Exception as e:
            logger.error(f"Error fatal: {e}", exc_info=True)
            sys.exit(1)
        finally:
            self.stop()
    
    def stop(self):
        """Detiene el servicio de telemetría."""
        if not self.running:
            return
            
        logger.info("Deteniendo servicio...")
        self.running = False
        
        # Detener cliente MQTT
        if self.mqtt_client:
            try:
                self.mqtt_client.stop()
            except Exception as e:
                logger.error(f"Error al detener cliente MQTT: {e}")
        
        # Desconectar báscula
        if self.scale_reader:
            try:
                self.scale_reader.disconnect()
            except Exception as e:
                logger.error(f"Error al desconectar báscula: {e}")
        
        logger.info("Servicio detenido")
    
    def _signal_handler(self, signum, frame):
        """Maneja señales del sistema para cierre graceful."""
        logger.info(f"Señal {signum} recibida, iniciando cierre...")
        self.stop()
        sys.exit(0)


def main():
    """Función principal."""
    service = ScaleTelemetryService()
    service.start()


if __name__ == "__main__":
    main()

