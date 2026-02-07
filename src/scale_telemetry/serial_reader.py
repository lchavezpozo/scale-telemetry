"""Lector de peso desde puerto serial."""

import logging
import re
from typing import Optional

import serial

from .config import SerialConfig

logger = logging.getLogger(__name__)


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
        
    def connect(self) -> None:
        """Establece la conexión con la báscula."""
        try:
            self.connection = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                timeout=self.config.timeout,
            )
            logger.info(f"Conectado a báscula en {self.config.port}")
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
            
            # Intenta extraer el número del peso
            # Busca patrones comunes: "45.3 kg", "45.3", "Weight: 45.3", etc.
            match = re.search(r'[-+]?\d*\.?\d+', line)
            if match:
                weight = float(match.group())
                logger.info(f"Peso leído: {weight} kg")
                return weight
            else:
                raise ValueError(f"No se pudo extraer el peso de: {line}")
                
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

