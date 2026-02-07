"""Tests para el cliente MQTT."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from scale_telemetry.config import MQTTConfig
from scale_telemetry.mqtt_client import ScaleMQTTClient


@pytest.fixture
def mqtt_config():
    """Fixture con configuración MQTT de prueba."""
    return MQTTConfig(
        broker="test.mosquitto.org",
        port=1883,
        device_id="scale-test"
    )


@pytest.fixture
def weight_callback():
    """Fixture que simula una función que retorna peso."""
    return Mock(return_value=42.5)


@pytest.fixture
def mqtt_client(mqtt_config, weight_callback):
    """Fixture con cliente MQTT configurado."""
    return ScaleMQTTClient(mqtt_config, weight_callback)


class TestScaleMQTTClient:
    """Tests para ScaleMQTTClient."""
    
    def test_init(self, mqtt_client, mqtt_config):
        """Test de inicialización del cliente."""
        assert mqtt_client.config == mqtt_config
        assert mqtt_client.client is not None
    
    def test_command_topic(self, mqtt_config):
        """Test que verifica el tópico de comandos."""
        expected = "pesanet/devices/scale-test/command"
        assert mqtt_config.command_topic == expected
    
    def test_response_topic(self, mqtt_config):
        """Test que verifica el tópico de respuestas."""
        expected = "pesanet/devices/scale-test/response"
        assert mqtt_config.response_topic == expected
    
    @patch('paho.mqtt.client.Client')
    def test_on_connect_success(self, mock_mqtt, mqtt_client):
        """Test de callback on_connect exitoso."""
        mock_client = MagicMock()
        
        # Simular conexión exitosa (rc=0)
        mqtt_client._on_connect(mock_client, None, None, 0)
        
        # Verificar que se suscribe al tópico de comandos
        mock_client.subscribe.assert_called_once_with(
            mqtt_client.config.command_topic
        )
    
    def test_handle_get_weight_command(self, mqtt_client, weight_callback):
        """Test de manejo del comando get_weight."""
        # Mock del método publish
        mqtt_client.client.publish = MagicMock()
        
        # Simular mensaje con comando get_weight
        msg = MagicMock()
        msg.topic = mqtt_client.config.command_topic
        msg.payload = json.dumps({"command": "get_weight"}).encode('utf-8')
        
        # Procesar el mensaje
        mqtt_client._on_message(None, None, msg)
        
        # Verificar que se llamó al callback de peso
        weight_callback.assert_called_once()
        
        # Verificar que se publicó una respuesta
        mqtt_client.client.publish.assert_called_once()
        
        # Verificar el contenido de la respuesta
        call_args = mqtt_client.client.publish.call_args
        topic = call_args[0][0]
        payload = json.loads(call_args[0][1])
        
        assert topic == mqtt_client.config.response_topic
        assert payload["deviceId"] == "scale-test"
        assert payload["weight"] == 42.5
        assert payload["status"] == "ok"
        assert "timestamp" in payload
    
    def test_handle_unknown_command(self, mqtt_client):
        """Test de manejo de comando desconocido."""
        # Mock del método publish
        mqtt_client.client.publish = MagicMock()
        
        # Simular mensaje con comando desconocido
        msg = MagicMock()
        msg.topic = mqtt_client.config.command_topic
        msg.payload = json.dumps({"command": "unknown_cmd"}).encode('utf-8')
        
        # Procesar el mensaje
        mqtt_client._on_message(None, None, msg)
        
        # Verificar que se publicó una respuesta de error
        call_args = mqtt_client.client.publish.call_args
        payload = json.loads(call_args[0][1])
        
        assert payload["status"] == "error"
        assert "desconocido" in payload["message"].lower()
    
    def test_handle_invalid_json(self, mqtt_client):
        """Test de manejo de JSON inválido."""
        # Mock del método publish
        mqtt_client.client.publish = MagicMock()
        
        # Simular mensaje con JSON inválido
        msg = MagicMock()
        msg.topic = mqtt_client.config.command_topic
        msg.payload = b"invalid json {"
        
        # Procesar el mensaje
        mqtt_client._on_message(None, None, msg)
        
        # Verificar que se publicó una respuesta de error
        call_args = mqtt_client.client.publish.call_args
        payload = json.loads(call_args[0][1])
        
        assert payload["status"] == "error"
        assert payload["weight"] is None

