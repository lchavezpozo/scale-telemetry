"""Tests para el lector serial."""

from unittest.mock import MagicMock, Mock, patch

import pytest
import serial

from scale_telemetry.config import SerialConfig
from scale_telemetry.serial_reader import ScaleReader


@pytest.fixture
def serial_config():
    """Fixture con configuración serial de prueba."""
    return SerialConfig(
        port="/dev/ttyUSB0",
        baudrate=9600,
        timeout=1.0
    )


@pytest.fixture
def mock_serial():
    """Fixture que simula una conexión serial."""
    with patch('serial.Serial') as mock:
        yield mock


class TestScaleReader:
    """Tests para ScaleReader."""
    
    def test_init(self, serial_config):
        """Test de inicialización del lector."""
        reader = ScaleReader(serial_config)
        assert reader.config == serial_config
        assert reader.connection is None
    
    def test_connect(self, serial_config, mock_serial):
        """Test de conexión a la báscula."""
        reader = ScaleReader(serial_config)
        reader.connect()
        
        # Verificar que se llamó a Serial con los parámetros correctos
        mock_serial.assert_called_once_with(
            port="/dev/ttyUSB0",
            baudrate=9600,
            timeout=1.0
        )
    
    def test_disconnect(self, serial_config, mock_serial):
        """Test de desconexión de la báscula."""
        mock_conn = MagicMock()
        mock_conn.is_open = True
        mock_serial.return_value = mock_conn
        
        reader = ScaleReader(serial_config)
        reader.connect()
        reader.disconnect()
        
        # Verificar que se cerró la conexión
        mock_conn.close.assert_called_once()
    
    def test_read_weight_success(self, serial_config, mock_serial):
        """Test de lectura exitosa de peso."""
        # Simular respuesta de la báscula
        mock_conn = MagicMock()
        mock_conn.is_open = True
        mock_conn.readline.return_value = b"45.3 kg\n"
        mock_serial.return_value = mock_conn
        
        reader = ScaleReader(serial_config)
        reader.connect()
        weight = reader.read_weight()
        
        assert weight == 45.3
        mock_conn.reset_input_buffer.assert_called_once()
    
    def test_read_weight_various_formats(self, serial_config, mock_serial):
        """Test de lectura con diferentes formatos de respuesta."""
        test_cases = [
            (b"45.3\n", 45.3),
            (b"Weight: 45.3 kg\n", 45.3),
            (b"45.3kg\n", 45.3),
            (b"  45.3  \n", 45.3),
            (b"+45.3\n", 45.3),
            (b"-2.5\n", -2.5),
            (b"100\n", 100.0),
        ]
        
        for input_data, expected_weight in test_cases:
            mock_conn = MagicMock()
            mock_conn.is_open = True
            mock_conn.readline.return_value = input_data
            mock_serial.return_value = mock_conn
            
            reader = ScaleReader(serial_config)
            reader.connect()
            weight = reader.read_weight()
            
            assert weight == expected_weight, f"Failed for input: {input_data}"
    
    def test_read_weight_invalid_data(self, serial_config, mock_serial):
        """Test de lectura con datos inválidos."""
        mock_conn = MagicMock()
        mock_conn.is_open = True
        mock_conn.readline.return_value = b"no number here\n"
        mock_serial.return_value = mock_conn
        
        reader = ScaleReader(serial_config)
        reader.connect()
        
        with pytest.raises(ValueError):
            reader.read_weight()
    
    def test_read_weight_not_connected(self, serial_config):
        """Test de lectura sin conexión."""
        reader = ScaleReader(serial_config)
        
        with pytest.raises(serial.SerialException):
            reader.read_weight()
    
    def test_context_manager(self, serial_config, mock_serial):
        """Test del uso como context manager."""
        mock_conn = MagicMock()
        mock_conn.is_open = True
        mock_serial.return_value = mock_conn
        
        with ScaleReader(serial_config) as reader:
            assert reader.connection is not None
        
        # Verificar que se cerró al salir del contexto
        mock_conn.close.assert_called_once()

