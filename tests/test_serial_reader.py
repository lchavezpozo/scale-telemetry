"""Tests para el lector serial."""

from unittest.mock import MagicMock, Mock, patch

import pytest
import serial

from scale_telemetry.config import SerialConfig
from scale_telemetry.serial_reader import (
    ScaleReader,
    parse_padded,
    parse_standard,
)


@pytest.fixture
def serial_config():
    """Fixture con configuración serial de prueba (formato standard)."""
    return SerialConfig(
        port="/dev/ttyUSB0",
        baudrate=9600,
        timeout=1.0
    )


@pytest.fixture
def padded_config():
    """Fixture con configuración serial formato padded."""
    return SerialConfig(
        port="/dev/ttyUSB0",
        baudrate=9600,
        timeout=1.0,
        weight_format="padded",
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

    def test_init_invalid_format(self):
        """Test que formato inválido lanza error."""
        config = SerialConfig(weight_format="inexistente")
        with pytest.raises(ValueError, match="no soportado"):
            ScaleReader(config)

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


class TestPaddedFormat:
    """Tests para el formato padded."""

    def test_read_weight_padded(self, padded_config, mock_serial):
        """Test de lectura con formato padded (una trama)."""
        mock_conn = MagicMock()
        mock_conn.is_open = True
        mock_conn.read_until.return_value = b'\x80\x02"0 000060000000\r'
        mock_serial.return_value = mock_conn

        reader = ScaleReader(padded_config)
        reader.connect()
        weight = reader.read_weight()

        assert weight == 60.0

    def test_read_weight_padded_various(self, padded_config, mock_serial):
        """Test de lectura padded con varios valores."""
        test_cases = [
            (b'\x80\x02"0 000060000000\r', 60.0),
            (b'\x80\x02"0 000120000000\r', 120.0),
            (b'\x80\x02"0 000005000000\r', 5.0),
            (b'\x80\x02"0 000100000000\r', 100.0),
            (b'\x80\x02"0 000000000000\r', 0.0),
        ]

        for input_data, expected_weight in test_cases:
            mock_conn = MagicMock()
            mock_conn.is_open = True
            mock_conn.read_until.return_value = input_data
            mock_serial.return_value = mock_conn

            reader = ScaleReader(padded_config)
            reader.connect()
            weight = reader.read_weight()

            assert weight == expected_weight, f"Failed for input: {input_data}"

    def test_read_weight_padded_multiple_frames(self, padded_config, mock_serial):
        """Test que con múltiples tramas toma la última."""
        mock_conn = MagicMock()
        mock_conn.is_open = True
        # Simular múltiples tramas concatenadas (como llega de la báscula real)
        mock_conn.read_until.return_value = (
            b'\x80\x02"0 000050000000\r'
            b'\x80\x02"0 000060000000\r'
        )
        mock_serial.return_value = mock_conn

        reader = ScaleReader(padded_config)
        reader.connect()
        weight = reader.read_weight()

        # Debe tomar la última trama (60, no 50)
        assert weight == 60.0

    def test_read_weight_padded_no_pattern(self, padded_config, mock_serial):
        """Test que datos sin patrón válido lanzan error después de reintentos."""
        mock_conn = MagicMock()
        mock_conn.is_open = True
        mock_conn.read_until.return_value = b'\x80\x02\r'
        mock_serial.return_value = mock_conn

        reader = ScaleReader(padded_config)
        reader.connect()

        with pytest.raises(ValueError, match="No se encontró trama válida"):
            reader.read_weight()

        # Debe haber intentado 5 veces
        assert mock_conn.read_until.call_count == 5

    def test_read_weight_padded_retry_on_garbage(self, padded_config, mock_serial):
        """Test que reintenta cuando llega datos parciales antes de trama válida."""
        mock_conn = MagicMock()
        mock_conn.is_open = True
        # Primero llega basura (b'000\r'), luego una trama válida
        mock_conn.read_until.side_effect = [
            b'000\r',
            b'\x80\x02"0 000060000000\r',
        ]
        mock_serial.return_value = mock_conn

        reader = ScaleReader(padded_config)
        reader.connect()
        weight = reader.read_weight()

        assert weight == 60.0
        assert mock_conn.read_until.call_count == 2


class TestParseFunctions:
    """Tests para las funciones de parseo independientes."""

    def test_parse_standard(self):
        """Test de parse_standard con varios formatos."""
        assert parse_standard("45.3 kg") == 45.3
        assert parse_standard("100") == 100.0
        assert parse_standard("-2.5") == -2.5

    def test_parse_standard_invalid(self):
        """Test que parse_standard lanza error sin números."""
        with pytest.raises(ValueError):
            parse_standard("no numbers")

    def test_parse_padded(self):
        """Test de parse_padded con varios formatos."""
        assert parse_padded(b'\x80\x02"0 000060000000\r') == 60.0
        assert parse_padded(b'\x80\x02"0 000120000000\r') == 120.0
        assert parse_padded(b'\x80\x02"0 000000000000\r') == 0.0

    def test_parse_padded_invalid(self):
        """Test que parse_padded lanza error sin patrón válido."""
        with pytest.raises(ValueError):
            parse_padded(b'\x80\x02\r')
