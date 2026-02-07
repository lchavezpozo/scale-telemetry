# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Scale Telemetry is an IoT service that reads weight data from industrial scales via serial port and publishes it via MQTT. It's designed for the "pesanet" platform. Requires Python >= 3.12. Built with Poetry (`pyproject.toml`).

## Commands

### Development Setup
```bash
make setup            # Full initial setup (creates .env, installs deps)
make dev              # Install with dev dependencies (pip install -e ".[dev]")
```

### Testing
```bash
make test             # Run pytest with coverage (HTML report in htmlcov/)
pytest tests/ -v      # Run tests directly
pytest tests/test_serial_reader.py -v  # Run single test file
pytest tests/test_serial_reader.py::test_read_weight -v  # Run single test
```

### Linting & Formatting
```bash
make lint             # Run flake8 (max-line-length=100), black --check, mypy
make format           # Format with black (default 88 char line length)
```

### Running & Docker
```bash
make run              # Run service locally
make up / make down   # Docker compose up/down
make simulator-pty    # Python PTY-based scale simulator (no hardware needed)
```

### Testing MQTT
```bash
make mqtt-test        # Send get_weight command (requires mosquitto_pub)
make mqtt-subscribe   # Subscribe to responses
make mqtt-client-test # Run Python test client
```

## Architecture

```
ScaleTelemetryService (main.py)
       │
       ├── ScaleReader (serial_reader.py)
       │     └── Reads weight from serial port using pyserial
       │     └── Parses weight values with regex (extracts first number from line)
       │
       └── ScaleMQTTClient (mqtt_client.py)
             └── Subscribes to command topic, publishes responses
             └── Uses paho-mqtt with WebSocket transport (ws://<broker>:<port>/mqtt)
             └── Callback pattern: _on_connect, _on_message, _on_disconnect
```

**MQTT Transport:** WebSocket (not raw TCP). Client connects to `ws://<broker>:<port>/mqtt`.

**MQTT Topics:**
- Command: `pesanet/devices/{device_id}/command` (listens for `{"command": "get_weight"}`)
- Response: `pesanet/devices/{device_id}/response` (publishes weight JSON with `deviceId`, `weight`, `status`, `message`, `timestamp`)

**Configuration:** Via environment variables or `.env` file. Dataclasses in `config.py` (`MQTTConfig`, `SerialConfig`) read env vars at import time with `os.getenv`.

**Flow:** MQTT message arrives -> `_on_message` parses JSON -> dispatches to `_handle_get_weight` -> calls `weight_callback` (which calls `ScaleReader.read_weight()`) -> publishes response JSON.

## Codebase Conventions

- Code comments, docstrings, and log messages are in **Spanish**. Maintain this convention.
- `src/` layout with `scale_telemetry` package.
- Configuration uses dataclasses with env var defaults (no config files).
