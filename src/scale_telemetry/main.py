"""Punto de entrada principal del sistema de telemetría."""

import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import serial

from .config import DeviceConfig, MQTTConfig, load_devices
from .mqtt_client import ScaleMQTTClient
from .serial_reader import ScaleReader

# Configurar logging
LOG_DIR = os.getenv("LOG_DIR", "logs")
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, 'scale_telemetry.log'))
    ]
)

logger = logging.getLogger(__name__)

RECONNECT_INTERVAL = 5  # segundos entre reintentos de conexión


class ScaleTelemetryService:
    """Servicio principal de telemetría de básculas."""

    def __init__(self):
        """Inicializa el servicio."""
        self.mqtt_config = MQTTConfig()
        self.devices = load_devices()
        self.device_configs: dict[str, DeviceConfig] = {
            d.device_id: d for d in self.devices
        }
        self.scale_readers: dict[str, ScaleReader] = {}
        self.mqtt_client: Optional[ScaleMQTTClient] = None
        self.running = False

    def _get_weight(self, device_id: str) -> float:
        """
        Obtiene el peso actual de una báscula específica.
        Si detecta un error serial, intenta reconectar automáticamente.

        Args:
            device_id: ID del dispositivo

        Returns:
            Peso en kilogramos
        """
        reader = self.scale_readers.get(device_id)
        if not reader:
            raise RuntimeError(f"Lector de báscula no encontrado: {device_id}")

        try:
            return reader.read_weight()
        except serial.SerialException as e:
            logger.warning(
                f"⚠️ Error serial en {device_id}: {e}. "
                f"Intentando reconectar..."
            )
            return self._reconnect_and_read(device_id)

    def _reconnect_and_read(self, device_id: str) -> float:
        """
        Reconecta un dispositivo serial y reintenta la lectura.

        Args:
            device_id: ID del dispositivo

        Returns:
            Peso en kilogramos

        Raises:
            RuntimeError: Si no se puede reconectar
        """
        device = self.device_configs[device_id]
        old_reader = self.scale_readers.get(device_id)

        # Cerrar conexión anterior
        if old_reader:
            try:
                old_reader.disconnect()
            except Exception:
                pass

        # Intentar reconectar
        serial_config = device.to_serial_config()
        new_reader = ScaleReader(serial_config)
        try:
            new_reader.connect()
        except Exception as e:
            raise RuntimeError(
                f"No se pudo reconectar {device_id} en "
                f"{device.serial_port}: {e}"
            )

        self.scale_readers[device_id] = new_reader
        logger.info(f"✅ Dispositivo {device_id} reconectado exitosamente")
        return new_reader.read_weight()

    def _retry_connect(self, device: DeviceConfig):
        """
        Reintenta conectar un dispositivo en background cada RECONNECT_INTERVAL segundos.
        Cuando logra conectar, registra el dispositivo en el cliente MQTT.

        Args:
            device: Configuración del dispositivo a reconectar
        """
        while self.running:
            time.sleep(RECONNECT_INTERVAL)
            if not self.running:
                break

            logger.info(
                f"🔄 Reintentando conexión de {device.device_id} "
                f"en {device.serial_port}..."
            )
            serial_config = device.to_serial_config()
            reader = ScaleReader(serial_config)
            try:
                reader.connect()
            except Exception as e:
                logger.warning(
                    f"❌ Reintento fallido para {device.device_id}: {e}"
                )
                continue

            # Conexión exitosa: registrar el dispositivo
            self.scale_readers[device.device_id] = reader
            did = device.device_id
            callback = lambda d=did: self._get_weight(d)
            self.mqtt_client.register_device(device, callback)
            logger.info(
                f"✅ Dispositivo {device.device_id} conectado después de reintento"
            )
            break

    def start(self):
        """Inicia el servicio de telemetría."""
        logger.info("=== Iniciando Scale Telemetry Service ===")
        logger.info(f"MQTT Broker: {self.mqtt_config.broker}:{self.mqtt_config.port}")
        logger.info(f"Dispositivos configurados: {len(self.devices)}")

        try:
            # Inicializar lectores de báscula
            weight_callbacks: dict[str, callable] = {}
            connected_devices = []
            failed_devices = []

            for device in self.devices:
                logger.info(f"  Dispositivo: {device.device_id} -> {device.serial_port}")
                serial_config = device.to_serial_config()
                reader = ScaleReader(serial_config)
                try:
                    reader.connect()
                except Exception as e:
                    logger.error(
                        f"❌ No se pudo conectar {device.device_id} "
                        f"en {device.serial_port}: {e}"
                    )
                    failed_devices.append(device)
                    continue
                self.scale_readers[device.device_id] = reader
                connected_devices.append(device)
                did = device.device_id
                weight_callbacks[did] = lambda d=did: self._get_weight(d)

            logger.info(
                f"Básculas conectadas: {len(connected_devices)}/{len(self.devices)}"
            )

            # Inicializar cliente MQTT con dispositivos conectados
            self.mqtt_client = ScaleMQTTClient(
                self.mqtt_config, connected_devices, weight_callbacks
            )
            self.mqtt_client.connect()

            # Configurar manejador de señales para cierre graceful
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            self.running = True

            # Lanzar hilos de reconexión para dispositivos fallidos
            for device in failed_devices:
                thread = threading.Thread(
                    target=self._retry_connect,
                    args=(device,),
                    daemon=True,
                    name=f"reconnect-{device.device_id}",
                )
                thread.start()
                logger.info(
                    f"🔄 Reintento de conexión iniciado para {device.device_id} "
                    f"(cada {RECONNECT_INTERVAL}s)"
                )

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

        # Desconectar todas las básculas
        for device_id, reader in self.scale_readers.items():
            try:
                reader.disconnect()
                logger.info(f"Báscula desconectada: {device_id}")
            except Exception as e:
                logger.error(f"Error al desconectar báscula {device_id}: {e}")

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
