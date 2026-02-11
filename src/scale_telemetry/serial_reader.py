"""Lector de peso desde puerto serial."""

import logging
import re
from typing import Optional

import serial

from .config import SerialConfig

logger = logging.getLogger(__name__)

# Formatos de parseo disponibles
WEIGHT_FORMATS = ["standard", "padded"]


def parse_standard(line: str) -> float:
    """
    Formato estándar: extrae el primer número de la línea.
    Soporta: "45.3 kg", "Weight: 45.3", "45.3", "-2.5", etc.
    """
    match = re.search(r'[-+]?\d*\.?\d+', line)
    if match:
        return float(match.group())
    raise ValueError(f"No se pudo extraer el peso de: {line}")


def parse_padded(line: str) -> float:
    """
    Formato con padding de ceros: bloque de 18 dígitos donde los primeros
    6 representan el peso entero con ceros a la izquierda.
    Soporta: '�"0 000060000000000000' -> 60.0, '000120000000000000' -> 120.0
    Busca el bloque más largo de dígitos consecutivos en la línea.
    """
    # Buscar todos los bloques de dígitos consecutivos
    blocks = re.findall(r'\d+', line)
    if not blocks:
        raise ValueError(f"No se encontraron dígitos en: {line}")

    # Tomar el bloque más largo (el que contiene los datos del peso)
    data_block = max(blocks, key=len)

    # Los primeros 6 dígitos contienen el peso con padding de ceros
    weight_digits = data_block[:6]
    return float(int(weight_digits))


PARSERS = {
    "standard": parse_standard,
    "padded": parse_padded,
}


class ScaleReader:
    """Lee el peso desde una báscula conectada por puerto serial."""

    def __init__(self, config: SerialConfig):
        """
        Inicializa el lector de báscula.

        Args:
            config: Configuración del puerto serial
        """
        self.config = config
        self.connection: Optional[serial.Serial] = None
        self._parser = PARSERS.get(config.weight_format)
        if not self._parser:
            raise ValueError(
                f"Formato de peso no soportado: '{config.weight_format}'. "
                f"Formatos disponibles: {WEIGHT_FORMATS}"
            )

    def connect(self) -> None:
        """Establece la conexión con la báscula."""
        try:
            self.connection = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                timeout=self.config.timeout,
            )
            logger.info(
                f"Conectado a báscula en {self.config.port} "
                f"(formato: {self.config.weight_format})"
            )
        except serial.SerialException as e:
            logger.error(f"Error al conectar con la báscula: {e}")
            raise

    def disconnect(self) -> None:
        """Cierra la conexión con la báscula."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("Desconectado de la báscula")

    def read_weight(self) -> float:
        """
        Lee el peso actual de la báscula.

        Returns:
            El peso en kilogramos

        Raises:
            serial.SerialException: Si hay un error de comunicación
            ValueError: Si no se puede parsear el peso
        """
        if not self.connection or not self.connection.is_open:
            raise serial.SerialException("No hay conexión con la báscula")

        try:
            # Limpia el buffer de entrada
            self.connection.reset_input_buffer()

            # Lee una línea del puerto serial
            line = self.connection.readline().decode('utf-8', errors='ignore').strip()
            logger.debug(f"Datos recibidos de báscula: {line}")

            weight = self._parser(line)
            logger.info(f"Peso leído: {weight} kg")
            return weight

        except serial.SerialException as e:
            logger.error(f"Error al leer de la báscula: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al leer peso: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
