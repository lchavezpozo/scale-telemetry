"""Tests para el cliente MQTT."""

import json
from concurrent.futures import Future
from unittest.mock import MagicMock, Mock, patch

import pytest

from scale_telemetry.config import DeviceConfig, MQTTConfig
from scale_telemetry.mqtt_client import WILDCARD_COMMAND_TOPIC, ScaleMQTTClient


def _sync_submit(fn, *args, **kwargs):
    """Ejecuta la función de forma síncrona y retorna un Future resuelto."""
    future = Future()
    try:
        result = fn(*args, **kwargs)
        future.set_result(result)
    except Exception as e:
        future.set_exception(e)
    return future


@pytest.fixture
def mqtt_config():
    """Fixture con configuración MQTT de prueba."""
    return MQTTConfig(
        broker="test.mosquitto.org",
        port=1883,
    )


@pytest.fixture
def devices():
    """Fixture con lista de dispositivos de prueba."""
    return [
        DeviceConfig(device_id="scale-test", serial_port="/dev/ttyUSB0"),
        DeviceConfig(device_id="scale-2", serial_port="/dev/ttyUSB1"),
    ]


@pytest.fixture
def weight_callbacks():
    """Fixture que simula funciones que retornan peso por dispositivo."""
    return {
        "scale-test": Mock(return_value=42.5),
        "scale-2": Mock(return_value=78.0),
    }


@pytest.fixture
def mqtt_client(mqtt_config, devices, weight_callbacks):
    """Fixture con cliente MQTT configurado."""
    client = ScaleMQTTClient(mqtt_config, devices, weight_callbacks)
    # Reemplazar executor con ejecución síncrona para tests deterministas
    client._executor.submit = _sync_submit
    return client


class TestScaleMQTTClient:
    """Tests para ScaleMQTTClient."""

    def test_init(self, mqtt_client, mqtt_config):
        """Test de inicialización del cliente."""
        assert mqtt_client.config == mqtt_config
        assert mqtt_client.client is not None
        assert "scale-test" in mqtt_client.devices
        assert "scale-2" in mqtt_client.devices

    @patch('paho.mqtt.client.Client')
    def test_on_connect_success(self, mock_mqtt, mqtt_client):
        """Test de callback on_connect exitoso."""
        mock_client = MagicMock()

        # Simular conexión exitosa (rc=0)
        mqtt_client._on_connect(mock_client, None, None, 0)

        # Verificar que se suscribe al tópico wildcard
        mock_client.subscribe.assert_called_once_with(WILDCARD_COMMAND_TOPIC)

    def test_handle_get_weight_command(self, mqtt_client, weight_callbacks):
        """Test de manejo del comando get_weight."""
        mqtt_client.client.publish = MagicMock()

        # Simular mensaje con comando get_weight para scale-test
        msg = MagicMock()
        msg.topic = "pesanet/devices/scale-test/command"
        msg.payload = json.dumps({"command": "get_weight"}).encode('utf-8')

        mqtt_client._on_message(None, None, msg)

        # Verificar que se llamó al callback correcto
        weight_callbacks["scale-test"].assert_called_once()
        weight_callbacks["scale-2"].assert_not_called()

        # Verificar el contenido de la respuesta
        call_args = mqtt_client.client.publish.call_args
        topic = call_args[0][0]
        payload = json.loads(call_args[0][1])

        assert topic == "pesanet/devices/scale-test/response"
        assert payload["deviceId"] == "scale-test"
        assert payload["weight"] == 42.5
        assert payload["status"] == "ok"
        assert "timestamp" in payload

    def test_handle_get_weight_second_device(self, mqtt_client, weight_callbacks):
        """Test de manejo del comando get_weight para el segundo dispositivo."""
        mqtt_client.client.publish = MagicMock()

        msg = MagicMock()
        msg.topic = "pesanet/devices/scale-2/command"
        msg.payload = json.dumps({"command": "get_weight"}).encode('utf-8')

        mqtt_client._on_message(None, None, msg)

        # Verificar que se llamó al callback del segundo dispositivo
        weight_callbacks["scale-2"].assert_called_once()
        weight_callbacks["scale-test"].assert_not_called()

        # Verificar respuesta en el tópico correcto
        call_args = mqtt_client.client.publish.call_args
        topic = call_args[0][0]
        payload = json.loads(call_args[0][1])

        assert topic == "pesanet/devices/scale-2/response"
        assert payload["deviceId"] == "scale-2"
        assert payload["weight"] == 78.0

    def test_unknown_device_ignored(self, mqtt_client, weight_callbacks):
        """Test que comandos para dispositivos no registrados se ignoran."""
        mqtt_client.client.publish = MagicMock()

        msg = MagicMock()
        msg.topic = "pesanet/devices/unknown-device/command"
        msg.payload = json.dumps({"command": "get_weight"}).encode('utf-8')

        mqtt_client._on_message(None, None, msg)

        # No se debe llamar a ningún callback ni publicar respuesta
        weight_callbacks["scale-test"].assert_not_called()
        weight_callbacks["scale-2"].assert_not_called()
        mqtt_client.client.publish.assert_not_called()

    def test_handle_unknown_command(self, mqtt_client):
        """Test de manejo de comando desconocido."""
        mqtt_client.client.publish = MagicMock()

        msg = MagicMock()
        msg.topic = "pesanet/devices/scale-test/command"
        msg.payload = json.dumps({"command": "unknown_cmd"}).encode('utf-8')

        mqtt_client._on_message(None, None, msg)

        # Verificar que se publicó una respuesta de error
        call_args = mqtt_client.client.publish.call_args
        payload = json.loads(call_args[0][1])

        assert payload["status"] == "error"
        assert payload["deviceId"] == "scale-test"
        assert "desconocido" in payload["message"].lower()

    def test_handle_invalid_json(self, mqtt_client):
        """Test de manejo de JSON inválido."""
        mqtt_client.client.publish = MagicMock()

        msg = MagicMock()
        msg.topic = "pesanet/devices/scale-test/command"
        msg.payload = b"invalid json {"

        mqtt_client._on_message(None, None, msg)

        # Verificar que se publicó una respuesta de error
        call_args = mqtt_client.client.publish.call_args
        payload = json.loads(call_args[0][1])

        assert payload["status"] == "error"
        assert payload["deviceId"] == "scale-test"
        assert payload["weight"] is None

    def test_register_device(self, mqtt_client):
        """Test de registro dinámico de un dispositivo nuevo."""
        new_device = DeviceConfig(device_id="scale-3", serial_port="/dev/ttyUSB2")
        new_callback = Mock(return_value=99.9)

        mqtt_client.register_device(new_device, new_callback)

        # Verificar que el dispositivo fue registrado
        assert "scale-3" in mqtt_client.devices
        assert "scale-3" in mqtt_client.weight_callbacks

        # Verificar que puede procesar comandos para el nuevo dispositivo
        mqtt_client.client.publish = MagicMock()
        msg = MagicMock()
        msg.topic = "pesanet/devices/scale-3/command"
        msg.payload = json.dumps({"command": "get_weight"}).encode('utf-8')

        mqtt_client._on_message(None, None, msg)

        new_callback.assert_called_once()
        call_args = mqtt_client.client.publish.call_args
        payload = json.loads(call_args[0][1])
        assert payload["deviceId"] == "scale-3"
        assert payload["weight"] == 99.9
