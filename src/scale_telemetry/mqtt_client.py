"""Cliente MQTT para telemetría de báscula."""

import json
import logging
import ssl
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import paho.mqtt.client as mqtt

from .config import DeviceConfig, MQTTConfig

logger = logging.getLogger(__name__)

WILDCARD_COMMAND_TOPIC = "pesanet/devices/+/command"


class ScaleMQTTClient:
    """Cliente MQTT para manejar comandos y respuestas de múltiples básculas."""

    def __init__(
        self,
        config: MQTTConfig,
        devices: list[DeviceConfig],
        weight_callbacks: dict[str, Callable[[], float]],
    ):
        """
        Inicializa el cliente MQTT.

        Args:
            config: Configuración del broker MQTT
            devices: Lista de dispositivos configurados
            weight_callbacks: Diccionario {device_id: callback} que retorna el peso
        """
        self.config = config
        self.devices: dict[str, DeviceConfig] = {d.device_id: d for d in devices}
        self.weight_callbacks = weight_callbacks
        self.client = mqtt.Client(
            client_id="scale-telemetry-service",
            transport="websockets"
        )

        # Configurar WebSocket path
        self.client.ws_set_options(path="/mqtt")

        # Configurar callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # Configurar SSL/TLS si está habilitado (wss://)
        if config.use_ssl:
            self.client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)

        # Pool de hilos para lecturas de peso en paralelo
        self._executor = ThreadPoolExecutor(
            max_workers=len(devices) or 1,
            thread_name_prefix="weight-reader",
        )

        # Configurar autenticación si está disponible
        if config.username and config.password:
            self.client.username_pw_set(config.username, config.password)

    def register_device(
        self,
        device: DeviceConfig,
        weight_callback: Callable[[], float],
    ):
        """
        Registra un dispositivo nuevo en el cliente MQTT.
        Puede llamarse en runtime desde otro hilo.

        Args:
            device: Configuración del dispositivo
            weight_callback: Función que retorna el peso
        """
        self.devices[device.device_id] = device
        self.weight_callbacks[device.device_id] = weight_callback
        logger.info(f"✅ Dispositivo registrado en MQTT: {device.device_id}")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback cuando se conecta al broker MQTT."""
        if rc == 0:
            logger.info("✅ CONECTADO exitosamente al broker MQTT")
            logger.info(f"   Broker: {self.config.broker}:{self.config.port}")
            # Suscribirse al tópico wildcard para todos los dispositivos
            client.subscribe(WILDCARD_COMMAND_TOPIC)
            logger.info(f"✅ Suscrito a: {WILDCARD_COMMAND_TOPIC}")
            logger.info(f"   Dispositivos registrados: {list(self.devices.keys())}")
        else:
            error_messages = {
                1: "Versión de protocolo incorrecta",
                2: "Identificador de cliente inválido",
                3: "Servidor no disponible",
                4: "Usuario o contraseña incorrectos",
                5: "No autorizado"
            }
            error_msg = error_messages.get(rc, f"Error desconocido (código {rc})")
            logger.error(f"❌ Error al conectar al broker MQTT: {error_msg}")
            logger.error(f"   Broker: {self.config.broker}:{self.config.port}")
            logger.error(f"   Usuario: {self.config.username}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback cuando se desconecta del broker MQTT."""
        if rc != 0:
            logger.warning(f"Desconexión inesperada del broker MQTT, código: {rc}")
        else:
            logger.info("Desconectado del broker MQTT")

    def _on_message(self, client, userdata, msg):
        """
        Callback cuando se recibe un mensaje MQTT.
        Extrae el device_id del tópico y rutea al callback correspondiente.
        """
        try:
            # Extraer device_id del tópico: pesanet/devices/{device_id}/command
            topic_parts = msg.topic.split("/")
            if len(topic_parts) != 4:
                logger.warning(f"Tópico con formato inesperado: {msg.topic}")
                return
            device_id = topic_parts[2]

            # Verificar que el dispositivo está registrado
            if device_id not in self.devices:
                logger.warning(f"Comando para dispositivo no registrado: {device_id}")
                return

            logger.info(f"Mensaje recibido en {msg.topic} (dispositivo: {device_id})")

            # Parsear el payload
            try:
                payload = json.loads(msg.payload.decode('utf-8'))
            except json.JSONDecodeError:
                logger.error(f"Payload inválido (no es JSON): {msg.payload}")
                self._send_error_response(device_id, "Formato de comando inválido")
                return

            # Verificar el comando
            command = payload.get('command')
            logger.info(f"Comando recibido: {command}")

            if command == 'get_weight':
                self._executor.submit(self._handle_get_weight, device_id)
            else:
                logger.warning(f"Comando desconocido: {command}")
                self._send_error_response(device_id, f"Comando desconocido: {command}")

        except Exception as e:
            logger.error(f"Error al procesar mensaje: {e}", exc_info=True)

    def _handle_get_weight(self, device_id: str):
        """Maneja el comando get_weight para un dispositivo específico."""
        try:
            # Obtener el peso de la báscula
            weight = self.weight_callbacks[device_id]()

            # Crear la respuesta
            response = {
                "deviceId": device_id,
                "weight": round(weight, 1),
                "status": "ok",
                "message": "Peso obtenido correctamente",
                "timestamp": int(time.time() * 1000)
            }

            # Publicar la respuesta
            self._publish_response(device_id, response)
            logger.info(f"Respuesta enviada [{device_id}]: {response}")

        except Exception as e:
            logger.error(f"Error al obtener peso de {device_id}: {e}")
            self._send_error_response(device_id, f"Error al leer peso: {str(e)}")

    def _send_error_response(self, device_id: str, error_message: str):
        """
        Envía una respuesta de error para un dispositivo específico.

        Args:
            device_id: ID del dispositivo
            error_message: Mensaje de error
        """
        response = {
            "deviceId": device_id,
            "weight": None,
            "status": "error",
            "message": error_message,
            "timestamp": int(time.time() * 1000)
        }
        self._publish_response(device_id, response)

    def _publish_response(self, device_id: str, response: dict):
        """
        Publica una respuesta en el tópico de respuestas del dispositivo.

        Args:
            device_id: ID del dispositivo
            response: Diccionario con la respuesta
        """
        topic = self.devices[device_id].response_topic
        payload = json.dumps(response)
        result = self.client.publish(topic, payload, qos=1)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.debug(f"Respuesta publicada en {topic}")
        else:
            logger.error(f"Error al publicar respuesta, código: {result.rc}")

    def connect(self):
        """Conecta al broker MQTT."""
        try:
            scheme = "wss" if self.config.use_ssl else "ws"
            url = f"{scheme}://{self.config.broker}:{self.config.port}/mqtt"
            logger.info("=== Intentando conectar a MQTT WebSocket ===")
            logger.info(f"URL: {url}")
            logger.info(f"SSL: {'habilitado' if self.config.use_ssl else 'deshabilitado'}")
            logger.info(f"Usuario: {self.config.username}")
            logger.info(f"Password: {'***' if self.config.password else 'None'}")
            logger.info("========================================")

            self.client.connect(self.config.broker, self.config.port, keepalive=60)
            logger.info(f"✅ Conexión WebSocket iniciada a {url}")
        except Exception as e:
            logger.error(f"❌ Error al conectar con el broker MQTT WebSocket: {e}")
            logger.error(f"URL intentada: {url}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def start(self):
        """Inicia el loop del cliente MQTT (bloqueante)."""
        logger.info("Iniciando cliente MQTT...")
        self.client.loop_forever()

    def stop(self):
        """Detiene el cliente MQTT."""
        logger.info("Deteniendo cliente MQTT...")
        self._executor.shutdown(wait=False)
        self.client.loop_stop()
        self.client.disconnect()
