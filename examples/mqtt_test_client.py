#!/usr/bin/env python3
"""
Cliente de prueba MQTT para enviar comandos y recibir respuestas.
"""

import json
import sys
import time

import paho.mqtt.client as mqtt


class TestClient:
    """Cliente MQTT de prueba."""
    
    def __init__(self, broker="localhost", port=1883, device_id="scale-1"):
        """
        Inicializa el cliente de prueba.
        
        Args:
            broker: Dirección del broker MQTT
            port: Puerto del broker
            device_id: ID del dispositivo a probar
        """
        self.broker = broker
        self.port = port
        self.device_id = device_id
        self.command_topic = f"pesanet/devices/{device_id}/command"
        self.response_topic = f"pesanet/devices/{device_id}/response"
        
        self.client = mqtt.Client(client_id="test-client")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.response_received = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback de conexión."""
        if rc == 0:
            print(f"✅ Conectado al broker MQTT en {self.broker}:{self.port}")
            client.subscribe(self.response_topic)
            print(f"✅ Suscrito a: {self.response_topic}\n")
        else:
            print(f"❌ Error al conectar, código: {rc}")
            sys.exit(1)
    
    def _on_message(self, client, userdata, msg):
        """Callback de mensaje recibido."""
        print(f"📨 Respuesta recibida en {msg.topic}:")
        
        try:
            response = json.loads(msg.payload.decode('utf-8'))
            print(json.dumps(response, indent=2))
            print()
            
            # Validar campos esperados
            required_fields = ["deviceId", "weight", "status", "message", "timestamp"]
            missing_fields = [f for f in required_fields if f not in response]
            
            if missing_fields:
                print(f"⚠️  Campos faltantes: {', '.join(missing_fields)}")
            else:
                print("✅ Todos los campos presentes")
            
            # Validar status
            if response["status"] == "ok":
                print(f"✅ Peso recibido: {response['weight']} kg")
            else:
                print(f"❌ Error: {response['message']}")
            
        except json.JSONDecodeError as e:
            print(f"❌ Error al parsear JSON: {e}")
            print(f"Payload raw: {msg.payload}")
        
        self.response_received = True
    
    def send_command(self, command: str):
        """
        Envía un comando al dispositivo.
        
        Args:
            command: Comando a enviar
        """
        payload = {"command": command}
        payload_str = json.dumps(payload)
        
        print(f"📤 Enviando comando a {self.command_topic}:")
        print(f"   {payload_str}\n")
        
        result = self.client.publish(self.command_topic, payload_str, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("✅ Comando enviado correctamente")
        else:
            print(f"❌ Error al enviar comando, código: {result.rc}")
    
    def run_test(self):
        """Ejecuta una prueba completa."""
        print("=== Cliente de Prueba MQTT ===\n")
        
        # Conectar al broker
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
        except Exception as e:
            print(f"❌ Error al conectar: {e}")
            sys.exit(1)
        
        # Iniciar loop en background
        self.client.loop_start()
        
        # Esperar a estar conectado
        time.sleep(1)
        
        # Enviar comando get_weight
        self.send_command("get_weight")
        
        # Esperar respuesta
        print("\n⏳ Esperando respuesta (timeout: 10s)...\n")
        timeout = 10
        elapsed = 0
        
        while not self.response_received and elapsed < timeout:
            time.sleep(0.1)
            elapsed += 0.1
        
        if not self.response_received:
            print("❌ Timeout: No se recibió respuesta")
        
        # Limpiar
        self.client.loop_stop()
        self.client.disconnect()
        print("\n✅ Test completado")


def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cliente de prueba MQTT")
    parser.add_argument(
        "--broker",
        default="localhost",
        help="Dirección del broker MQTT (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="Puerto del broker (default: 1883)"
    )
    parser.add_argument(
        "--device-id",
        default="scale-1",
        help="ID del dispositivo (default: scale-1)"
    )
    
    args = parser.parse_args()
    
    # Ejecutar test
    client = TestClient(args.broker, args.port, args.device_id)
    client.run_test()


if __name__ == "__main__":
    main()

