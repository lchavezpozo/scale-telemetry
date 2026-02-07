.PHONY: help build up down restart logs test clean install dev docker-build docker-up docker-down docker-logs docker-restart

# Colores para output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Muestra esta ayuda
	@echo "$(BLUE)Scale Telemetry - Comandos disponibles:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# Instalación y Desarrollo Local
# ============================================================================

install: ## Instala el paquete localmente
	@echo "$(BLUE)Instalando paquete...$(NC)"
	pip install -e .
	@echo "$(GREEN)✅ Instalación completada$(NC)"

dev: ## Instala dependencias de desarrollo
	@echo "$(BLUE)Instalando dependencias de desarrollo...$(NC)"
	pip install -e ".[dev]"
	@echo "$(GREEN)✅ Dependencias de desarrollo instaladas$(NC)"

test: ## Ejecuta los tests
	@echo "$(BLUE)Ejecutando tests...$(NC)"
	pytest tests/ -v --cov=scale_telemetry --cov-report=html
	@echo "$(GREEN)✅ Tests completados$(NC)"

run: ## Ejecuta el servicio localmente
	@echo "$(BLUE)Iniciando servicio...$(NC)"
	scale-telemetry

clean: ## Limpia archivos temporales
	@echo "$(BLUE)Limpiando archivos temporales...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist
	@echo "$(GREEN)✅ Limpieza completada$(NC)"

# ============================================================================
# Docker
# ============================================================================

docker-build: ## Construye las imágenes Docker
	@echo "$(BLUE)Construyendo imágenes Docker...$(NC)"
	docker-compose build
	@echo "$(GREEN)✅ Imágenes construidas$(NC)"

docker-up: ## Inicia los servicios Docker
	@echo "$(BLUE)Iniciando servicios Docker...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✅ Servicios iniciados$(NC)"
	@echo ""
	@docker-compose ps

docker-down: ## Detiene los servicios Docker
	@echo "$(BLUE)Deteniendo servicios Docker...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ Servicios detenidos$(NC)"

docker-restart: ## Reinicia los servicios Docker
	@echo "$(BLUE)Reiniciando servicios Docker...$(NC)"
	docker-compose restart
	@echo "$(GREEN)✅ Servicios reiniciados$(NC)"

docker-logs: ## Muestra los logs de Docker
	@echo "$(BLUE)Mostrando logs...$(NC)"
	docker-compose logs -f

docker-logs-telemetry: ## Muestra solo logs del servicio de telemetría
	docker-compose logs -f scale-telemetry

docker-logs-mqtt: ## Muestra solo logs de MQTT (si usas mosquitto local)
	@echo "$(YELLOW)Nota: Este proyecto está configurado para EMQX externo$(NC)"
	@echo "Si tienes mosquitto en Docker, usa: docker logs <nombre-contenedor>"

docker-status: ## Muestra el estado de los contenedores
	@echo "$(BLUE)Estado de los contenedores:$(NC)"
	@docker-compose ps

docker-shell-telemetry: ## Abre una shell en el contenedor de telemetría
	docker-compose exec scale-telemetry bash

docker-shell-mqtt: ## Abre una shell en el contenedor MQTT (si usas EMQX en Docker)
	@echo "$(YELLOW)Nota: Este proyecto usa EMQX externo$(NC)"
	@echo "Si tu EMQX está en Docker, usa: docker exec -it <nombre-contenedor-emqx> /bin/sh"

docker-clean: ## Limpia contenedores, volúmenes e imágenes
	@echo "$(YELLOW)⚠️  Esto eliminará contenedores, volúmenes y logs$(NC)"
	@read -p "¿Continuar? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)Limpiando Docker...$(NC)"; \
		docker-compose down -v; \
		rm -rf logs/*; \
		echo "$(GREEN)✅ Limpieza completada$(NC)"; \
	else \
		echo "$(RED)Cancelado$(NC)"; \
	fi

# Alias para comandos Docker más cortos
build: docker-build ## Alias de docker-build
up: docker-up ## Alias de docker-up
down: docker-down ## Alias de docker-down
restart: docker-restart ## Alias de docker-restart
logs: docker-logs ## Alias de docker-logs
status: docker-status ## Alias de docker-status

# ============================================================================
# Testing MQTT
# ============================================================================

mqtt-test: ## Envía un comando de prueba MQTT (requiere mosquitto_pub instalado)
	@echo "$(BLUE)Enviando comando get_weight...$(NC)"
	@echo "$(YELLOW)Asegúrate de tener mosquitto_pub instalado o usa EMQX Dashboard$(NC)"
	@which mosquitto_pub > /dev/null || (echo "$(RED)mosquitto_pub no encontrado. Instala: brew install mosquitto$(NC)" && exit 1)
	mosquitto_pub -h localhost -t "pesanet/devices/scale-1/command" -m '{"command":"get_weight"}'
	@echo "$(GREEN)✅ Comando enviado$(NC)"

mqtt-subscribe: ## Se suscribe a las respuestas MQTT (requiere mosquitto_sub instalado)
	@echo "$(BLUE)Suscribiéndose a respuestas...$(NC)"
	@echo "$(YELLOW)Asegúrate de tener mosquitto_sub instalado o usa EMQX Dashboard$(NC)"
	@which mosquitto_sub > /dev/null || (echo "$(RED)mosquitto_sub no encontrado. Instala: brew install mosquitto$(NC)" && exit 1)
	mosquitto_sub -h localhost -t "pesanet/devices/scale-1/response" -v

# ============================================================================
# Desarrollo y debugging
# ============================================================================

simulator: ## Ejecuta el simulador de báscula con socat (requiere sudo)
	@echo "$(BLUE)Iniciando simulador de báscula con socat...$(NC)"
	@echo "$(YELLOW)Nota: Requiere permisos sudo$(NC)"
	sudo bash examples/socat_scale_simulator.sh

simulator-pty: ## Ejecuta el simulador de báscula con PTY de Python
	@echo "$(BLUE)Iniciando simulador de báscula con PTY...$(NC)"
	python examples/scale_simulator.py

mqtt-client-test: ## Ejecuta el cliente de prueba MQTT
	@echo "$(BLUE)Ejecutando cliente de prueba...$(NC)"
	python examples/mqtt_test_client.py

check-ports: ## Lista los puertos seriales disponibles
	@echo "$(BLUE)Puertos seriales disponibles:$(NC)"
	@if [[ "$$OSTYPE" == "darwin"* ]]; then \
		ls /dev/cu.* 2>/dev/null || echo "  No se encontraron puertos"; \
	else \
		ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "  No se encontraron puertos"; \
	fi

# ============================================================================
# Setup inicial
# ============================================================================

setup: ## Configuración inicial del proyecto
	@echo "$(BLUE)=== Configuración Inicial ===$(NC)"
	@mkdir -p docker/mosquitto/data docker/mosquitto/log logs
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Creando archivo .env...$(NC)"; \
		cp docker.env.example .env; \
		echo "$(GREEN)✅ .env creado$(NC)"; \
		echo "$(YELLOW)⚠️  Recuerda editar .env con tu configuración$(NC)"; \
	else \
		echo "$(GREEN)✅ .env ya existe$(NC)"; \
	fi
	@echo ""
	@echo "$(BLUE)Instalando dependencias...$(NC)"
	@pip install -e ".[dev]"
	@echo "$(GREEN)✅ Setup completado$(NC)"
	@echo ""
	@echo "Próximos pasos:"
	@echo "  1. Edita .env con tu configuración"
	@echo "  2. Ejecuta 'make up' para iniciar Docker"
	@echo "  3. Ejecuta 'make mqtt-test' para probar"

# ============================================================================
# CI/CD
# ============================================================================

ci-test: ## Ejecuta tests para CI
	pytest tests/ -v --cov=scale_telemetry --cov-report=xml --cov-report=term

lint: ## Ejecuta linters
	@echo "$(BLUE)Ejecutando linters...$(NC)"
	@which flake8 > /dev/null || pip install flake8
	@which black > /dev/null || pip install black
	@which mypy > /dev/null || pip install mypy
	flake8 src/scale_telemetry --max-line-length=100
	black --check src/scale_telemetry
	mypy src/scale_telemetry --ignore-missing-imports
	@echo "$(GREEN)✅ Linting completado$(NC)"

format: ## Formatea el código
	@echo "$(BLUE)Formateando código...$(NC)"
	@which black > /dev/null || pip install black
	black src/scale_telemetry
	@echo "$(GREEN)✅ Código formateado$(NC)"

