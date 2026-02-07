"""Configuración del sistema de telemetría."""

import os
from dataclasses import dataclass


@dataclass
class MQTTConfig:
    """Configuración MQTT."""
    broker: str = os.getenv("MQTT_BROKER", "localhost")
    port: int = int(os.getenv("MQTT_PORT", "1883"))
    username: str | None = os.getenv("MQTT_USERNAME")
    password: str | None = os.getenv("MQTT_PASSWORD")
    use_ssl: bool = os.getenv("MQTT_USE_SSL", "false").lower() == "true"
    device_id: str = os.getenv("DEVICE_ID", "scale-1")
    
    @property
    def command_topic(self) -> str:
        """Tópico para recibir comandos."""
        return f"pesanet/devices/{self.device_id}/command"
    
    @property
    def response_topic(self) -> str:
        """Tópico para enviar respuestas."""
        return f"pesanet/devices/{self.device_id}/response"


@dataclass
class SerialConfig:
    """Configuración del puerto serial."""
    port: str = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
    baudrate: int = int(os.getenv("SERIAL_BAUDRATE", "9600"))
    timeout: float = float(os.getenv("SERIAL_TIMEOUT", "1.0"))

