"""Configuración del sistema de telemetría."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno desde .env antes de leer os.getenv()
load_dotenv()


@dataclass
class MQTTConfig:
    """Configuración del broker MQTT (compartida entre dispositivos)."""
    broker: str = os.getenv("MQTT_BROKER", "localhost")
    port: int = int(os.getenv("MQTT_PORT", "1883"))
    username: str | None = os.getenv("MQTT_USERNAME")
    password: str | None = os.getenv("MQTT_PASSWORD")
    use_ssl: bool = os.getenv("MQTT_USE_SSL", "false").lower() == "true"


@dataclass
class SerialConfig:
    """Configuración del puerto serial."""
    port: str = "/dev/ttyUSB0"
    baudrate: int = 9600
    timeout: float = 1.0
    weight_format: str = "standard"


@dataclass
class DeviceConfig:
    """Configuración de un dispositivo (báscula)."""
    device_id: str
    serial_port: str
    baudrate: int = 9600
    timeout: float = 1.0
    weight_format: str = "standard"

    @property
    def command_topic(self) -> str:
        """Tópico para recibir comandos."""
        return f"pesanet/devices/{self.device_id}/command"

    @property
    def response_topic(self) -> str:
        """Tópico para enviar respuestas."""
        return f"pesanet/devices/{self.device_id}/response"

    def to_serial_config(self) -> SerialConfig:
        """Convierte a SerialConfig para el ScaleReader."""
        return SerialConfig(
            port=self.serial_port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            weight_format=self.weight_format,
        )


def load_devices(config_path: str | None = None) -> list[DeviceConfig]:
    """
    Carga la configuración de dispositivos desde archivo JSON.

    Raises:
        FileNotFoundError: Si no se encuentra el archivo de configuración
    """
    path = config_path or os.getenv("DEVICES_CONFIG_PATH", "devices.json")

    if not Path(path).exists():
        raise FileNotFoundError(
            f"Archivo de configuración de dispositivos no encontrado: {path}. "
            f"Crea el archivo a partir de devices.json.example"
        )

    with open(path, "r") as f:
        data = json.load(f)

    if not data:
        raise ValueError(f"El archivo {path} no contiene dispositivos")

    return [
        DeviceConfig(
            device_id=d["device_id"],
            serial_port=d["serial_port"],
            baudrate=d.get("baudrate", 9600),
            timeout=d.get("timeout", 1.0),
            weight_format=d.get("weight_format", "standard"),
        )
        for d in data
    ]
