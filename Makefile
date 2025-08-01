.PHONY: help install test run docker-build docker-run docker-stop clean

# Default target
help:
	@echo "AI Call Bot - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install     - Install Python dependencies"
	@echo "  test        - Run setup tests"
	@echo "  run         - Run the application locally"
	@echo "  run-debug   - Run the application in debug mode"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run with Docker Compose"
	@echo "  docker-stop  - Stop Docker services"
	@echo "  docker-logs  - View Docker logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean       - Clean up temporary files"
	@echo "  reset-db    - Reset database (removes all conversations)"

# Development commands
install:
	pip install -r requirements.txt

test:
	python src/test_setup.py

run:
	python main.py

run-debug:
	FLASK_DEBUG=True python main.py

# Docker commands
docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f ai-call-bot

# Maintenance commands
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "temp_audio_*.mp3" -delete
	find . -type f -name "temp_audio_*.wav" -delete
	find . -type f -name "*.log" -delete

reset-db:
	rm -f conversations.db
	rm -f data/conversations.db
	@echo "Database reset complete"

# Quick start
quick-start: install test run

# Docker quick start
docker-quick: docker-build docker-run
	@echo "Application started with Docker!"
	@echo "Access web interface at: http://localhost:5000"
	@echo "View logs with: make docker-logs" 