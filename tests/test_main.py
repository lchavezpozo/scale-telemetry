"""Tests para el servicio principal de telemetría."""

from unittest.mock import MagicMock, patch

import pytest
import serial

from scale_telemetry.config import DeviceConfig, MQTTConfig
from scale_telemetry.main import ScaleTelemetryService
from scale_telemetry.serial_reader import ScaleReader


@pytest.fixture
def service():
    """Fixture con servicio configurado manualmente."""
    with patch.object(ScaleTelemetryService, '__init__', lambda self: None):
        svc = ScaleTelemetryService()
        svc.mqtt_config = MQTTConfig(broker="localhost", port=1883)
        svc.devices = [
            DeviceConfig(device_id="scale-1", serial_port="/dev/ttyUSB0"),
        ]
        svc.device_configs = {"scale-1": svc.devices[0]}
        svc.scale_readers = {}
        svc.mqtt_client = None
        svc.running = False
        return svc


class TestGetWeightReconnect:
    """Tests para reconexión automática de dispositivos serial."""

    def test_get_weight_success(self, service):
        """Test de lectura exitosa sin reconexión."""
        mock_reader = MagicMock(spec=ScaleReader)
        mock_reader.read_weight.return_value = 50.0
        service.scale_readers["scale-1"] = mock_reader

        weight = service._get_weight("scale-1")

        assert weight == 50.0
        mock_reader.read_weight.assert_called_once()

    def test_get_weight_no_reader(self, service):
        """Test que lanza error si no hay reader."""
        with pytest.raises(RuntimeError, match="no encontrado"):
            service._get_weight("scale-1")

    @patch('scale_telemetry.main.ScaleReader')
    def test_get_weight_reconnects_on_serial_error(
        self, mock_reader_class, service
    ):
        """Test que reconecta cuando hay error serial."""
        # Reader original que falla
        broken_reader = MagicMock(spec=ScaleReader)
        broken_reader.read_weight.side_effect = serial.SerialException(
            "USB desconectado"
        )
        service.scale_readers["scale-1"] = broken_reader

        # Nuevo reader que funciona después de reconectar
        new_reader = MagicMock(spec=ScaleReader)
        new_reader.read_weight.return_value = 75.0
        mock_reader_class.return_value = new_reader

        weight = service._get_weight("scale-1")

        assert weight == 75.0
        # Verificar que desconectó el reader viejo
        broken_reader.disconnect.assert_called_once()
        # Verificar que creó y conectó uno nuevo
        new_reader.connect.assert_called_once()
        # Verificar que reemplazó el reader
        assert service.scale_readers["scale-1"] is new_reader

    @patch('scale_telemetry.main.ScaleReader')
    def test_get_weight_reconnect_fails(self, mock_reader_class, service):
        """Test que lanza error si la reconexión falla."""
        # Reader original que falla
        broken_reader = MagicMock(spec=ScaleReader)
        broken_reader.read_weight.side_effect = serial.SerialException(
            "USB desconectado"
        )
        service.scale_readers["scale-1"] = broken_reader

        # Reconexión también falla
        new_reader = MagicMock(spec=ScaleReader)
        new_reader.connect.side_effect = serial.SerialException(
            "Puerto no disponible"
        )
        mock_reader_class.return_value = new_reader

        with pytest.raises(RuntimeError, match="No se pudo reconectar"):
            service._get_weight("scale-1")
