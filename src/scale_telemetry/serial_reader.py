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


def parse_padded(raw_data: bytes) -> float:
    """
    Formato con padding de ceros para básculas industriales.
    Cada trama tiene el patrón: [header]"0 DDDDDDDDDDDD\r
    donde D son 12 dígitos con el peso (ceros a la izquierda).
    Extrae la última trama válida (lectura más reciente).
    """
    # Buscar todas las tramas con el patrón "0 seguido de 12 dígitos
    matches = re.findall(rb'"0 (\d{12})', raw_data)
    logger.info(f"Padded parser - tramas encontradas: {len(matches)}")

    if not matches:
        raise ValueError(
            f"No se encontró patrón de trama válido en los datos "
            f"({len(raw_data)} bytes)"
        )

    # Tomar la última trama (lectura más reciente)
    last_frame = matches[-1].decode('ascii')
    logger.info(f"Padded parser - última trama: '{last_frame}'")

    # Los primeros 6 dígitos contienen el peso con padding de ceros
    weight_digits = last_frame[:6]
    weight = float(int(weight_digits))
    logger.info(f"Padded parser - peso extraído: {weight}")
    return weight


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

            if self.config.weight_format == "padded":
                # Formato padded: leer una trama completa hasta \r
                raw_bytes = self.connection.read_until(b'\r')
                logger.info(f"Datos crudos padded ({len(raw_bytes)} bytes): {raw_bytes!r}")
                weight = parse_padded(raw_bytes)
            else:
                # Formato standard: leer una línea hasta \n
                raw_bytes = self.connection.readline()
                logger.info(f"Datos crudos (bytes): {raw_bytes!r}")
                line = raw_bytes.decode('utf-8', errors='ignore').strip()
                logger.info(f"Datos decodificados: '{line}'")
                weight = parse_standard(line)

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
