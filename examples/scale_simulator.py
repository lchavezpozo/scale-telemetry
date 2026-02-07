#!/usr/bin/env python3
"""
Simulador de báscula para pruebas.
Este script crea un puerto serial virtual que simula una báscula.
"""

import os
import pty
import random
import sys
import time
from argparse import ArgumentParser, Namespace


def simulate_scale(slave_fd: int, random_mode: bool, fixed_weight: float):
    """
    Simula una báscula que envía pesos aleatorios.
    
    Args:
        slave_fd: File descriptor del puerto serial esclavo
    """
    print("Simulador de báscula iniciado")
    if random_mode:
        print("Enviando pesos aleatorios cada segundo...")
    else:
        print(f"Enviando peso fijo de {fixed_weight:.1f} kg cada segundo...")
    
    try:
        while True:
            if random_mode:
                # Generar peso aleatorio entre 0 y 150 kg
                weight = random.uniform(0, 150)
            else:
                weight = fixed_weight
            
            # Formatear como lo haría una báscula real
            message = f"{weight:.1f} kg\n"
            
            # Escribir al puerto serial
            os.write(slave_fd, message.encode('utf-8'))
            print(f"Enviado: {message.strip()}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nSimulador detenido")


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Simulador de báscula para pruebas.")
    parser.add_argument(
        "--random",
        action="store_true",
        help="Si se establece, envía pesos aleatorios en lugar de un peso fijo.",
    )
    parser.add_argument(
        "--weight",
        type=float,
        default=120.0,
        help="Peso fijo a enviar cuando no se usa modo aleatorio. Por defecto 120 kg.",
    )
    return parser


def parse_args(argv: list[str]) -> Namespace:
    parser = build_parser()
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    """Función principal."""
    args = parse_args(argv if argv is not None else sys.argv[1:])

    print("=== Simulador de Báscula ===\n")
    
    # Crear un par de pseudo-terminales (PTY)
    master_fd, slave_fd = pty.openpty()
    
    # Obtener el nombre del dispositivo esclavo
    slave_name = os.ttyname(slave_fd)
    
    print(f"Puerto serial virtual creado: {slave_name}")
    print(f"\nUsa este puerto en la configuración:")
    print(f"  export SERIAL_PORT={slave_name}\n")
    print("Presiona Ctrl+C para detener\n")
    
    # Iniciar simulación
    simulate_scale(master_fd, args.random, args.weight)


if __name__ == "__main__":
    main()

