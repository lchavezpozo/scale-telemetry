"""Tests para la configuración de dispositivos."""

import json

import pytest

from scale_telemetry.config import DeviceConfig, SerialConfig, load_devices


class TestDeviceConfig:
    """Tests para DeviceConfig."""

    def test_command_topic(self):
        """Test que verifica el tópico de comandos."""
        device = DeviceConfig(device_id="scale-1", serial_port="/dev/ttyUSB0")
        assert device.command_topic == "pesanet/devices/scale-1/command"

    def test_response_topic(self):
        """Test que verifica el tópico de respuestas."""
        device = DeviceConfig(device_id="scale-2", serial_port="/dev/ttyUSB1")
        assert device.response_topic == "pesanet/devices/scale-2/response"

    def test_to_serial_config(self):
        """Test de conversión a SerialConfig."""
        device = DeviceConfig(
            device_id="scale-1",
            serial_port="/dev/ttyUSB0",
            baudrate=19200,
            timeout=2.0,
        )
        serial_config = device.to_serial_config()

        assert isinstance(serial_config, SerialConfig)
        assert serial_config.port == "/dev/ttyUSB0"
        assert serial_config.baudrate == 19200
        assert serial_config.timeout == 2.0

    def test_defaults(self):
        """Test de valores por defecto."""
        device = DeviceConfig(device_id="scale-1", serial_port="/dev/ttyUSB0")
        assert device.baudrate == 9600
        assert device.timeout == 1.0


class TestLoadDevices:
    """Tests para load_devices."""

    def test_load_from_json(self, tmp_path):
        """Test de carga desde archivo JSON."""
        devices_file = tmp_path / "devices.json"
        devices_data = [
            {
                "device_id": "scale-1",
                "serial_port": "/dev/ttyUSB0",
                "baudrate": 9600,
                "timeout": 1.0,
            },
            {
                "device_id": "scale-2",
                "serial_port": "/dev/ttyUSB1",
                "baudrate": 19200,
                "timeout": 2.0,
            },
        ]
        devices_file.write_text(json.dumps(devices_data))

        devices = load_devices(str(devices_file))

        assert len(devices) == 2
        assert devices[0].device_id == "scale-1"
        assert devices[0].serial_port == "/dev/ttyUSB0"
        assert devices[1].device_id == "scale-2"
        assert devices[1].baudrate == 19200

    def test_load_json_defaults(self, tmp_path):
        """Test que baudrate y timeout usan valores por defecto si no están en el JSON."""
        devices_file = tmp_path / "devices.json"
        devices_data = [
            {"device_id": "scale-1", "serial_port": "/dev/ttyUSB0"}
        ]
        devices_file.write_text(json.dumps(devices_data))

        devices = load_devices(str(devices_file))

        assert devices[0].baudrate == 9600
        assert devices[0].timeout == 1.0

    def test_file_not_found(self, tmp_path):
        """Test que lanza error si no existe el archivo."""
        nonexistent_path = str(tmp_path / "no_existe.json")

        with pytest.raises(FileNotFoundError):
            load_devices(nonexistent_path)

    def test_empty_file(self, tmp_path):
        """Test que lanza error si el archivo está vacío."""
        devices_file = tmp_path / "devices.json"
        devices_file.write_text("[]")

        with pytest.raises(ValueError):
            load_devices(str(devices_file))
