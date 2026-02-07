"""Cliente MQTT para telemetría de báscula."""

import json
import logging
import ssl
import time
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from .config import MQTTConfig

logger = logging.getLogger(__name__)


class ScaleMQTTClient:
    """Cliente MQTT para manejar comandos y respuestas de la báscula."""
    
    def __init__(self, config: MQTTConfig, weight_callback: Callable[[], float]):
        """
        Inicializa el cliente MQTT.
        
        Args:
            config: Configuración MQTT
            weight_callback: Función que retorna el peso actual
        """
        self.config = config
        self.weight_callback = weight_callback
        self.client = mqtt.Client(
            client_id=f"scale-telemetry-{config.device_id}",
            transport="websockets"  # Usar WebSocket en lugar de TCP
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

        # Configurar autenticación si está disponible
        if config.username and config.password:
            self.client.username_pw_set(config.username, config.password)
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback cuando se conecta al broker MQTT."""
        if rc == 0:
            logger.info(f"✅ CONECTADO exitosamente al broker MQTT")
            logger.info(f"   Broker: {self.config.broker}:{self.config.port}")
            # Suscribirse al tópico de comandos
            client.subscribe(self.config.command_topic)
            logger.info(f"✅ Suscrito a: {self.config.command_topic}")
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
        
        Args:
            client: Cliente MQTT
            userdata: Datos de usuario
            msg: Mensaje recibido
        """
        try:
            logger.info(f"Mensaje recibido en {msg.topic}")
            
            # Parsear el payload
            try:
                payload = json.loads(msg.payload.decode('utf-8'))
            except json.JSONDecodeError:
                logger.error(f"Payload inválido (no es JSON): {msg.payload}")
                self._send_error_response("Formato de comando inválido")
                return
            
            # Verificar el comando
            command = payload.get('command')
            logger.info(f"Comando recibido: {command}")
            
            if command == 'get_weight':
                self._handle_get_weight()
            else:
                logger.warning(f"Comando desconocido: {command}")
                self._send_error_response(f"Comando desconocido: {command}")
                
        except Exception as e:
            logger.error(f"Error al procesar mensaje: {e}", exc_info=True)
            self._send_error_response(f"Error al procesar comando: {str(e)}")
    
    def _handle_get_weight(self):
        """Maneja el comando get_weight."""
        try:
            # Obtener el peso de la báscula
            weight = self.weight_callback()
            
            # Crear la respuesta
            response = {
                "deviceId": self.config.device_id,
                "weight": round(weight, 1),
                "status": "ok",
                "message": "Peso obtenido correctamente",
                "timestamp": int(time.time() * 1000)  # timestamp en milisegundos
            }
            
            # Publicar la respuesta
            self._publish_response(response)
            logger.info(f"Respuesta enviada: {response}")
            
        except Exception as e:
            logger.error(f"Error al obtener peso: {e}")
            self._send_error_response(f"Error al leer peso: {str(e)}")
    
    def _send_error_response(self, error_message: str):
        """
        Envía una respuesta de error.
        
        Args:
            error_message: Mensaje de error
        """
        response = {
            "deviceId": self.config.device_id,
            "weight": None,
            "status": "error",
            "message": error_message,
            "timestamp": int(time.time() * 1000)
        }
        self._publish_response(response)
    
    def _publish_response(self, response: dict):
        """
        Publica una respuesta en el tópico de respuestas.
        
        Args:
            response: Diccionario con la respuesta
        """
        payload = json.dumps(response)
        result = self.client.publish(self.config.response_topic, payload, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.debug(f"Respuesta publicada en {self.config.response_topic}")
        else:
            logger.error(f"Error al publicar respuesta, código: {result.rc}")
    
    def connect(self):
        """Conecta al broker MQTT."""
        try:
            scheme = "wss" if self.config.use_ssl else "ws"
            url = f"{scheme}://{self.config.broker}:{self.config.port}/mqtt"
            logger.info(f"=== Intentando conectar a MQTT WebSocket ===")
            logger.info(f"URL: {url}")
            logger.info(f"SSL: {'habilitado' if self.config.use_ssl else 'deshabilitado'}")
            logger.info(f"Usuario: {self.config.username}")
            logger.info(f"Password: {'***' if self.config.password else 'None'}")
            logger.info(f"========================================")

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
        self.client.loop_stop()
        self.client.disconnect()

