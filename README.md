# AI Call Bot 🤖

A sophisticated AI-powered voice conversation system that integrates with Ollama for local LLM inference, featuring real-time speech recognition, text-to-speech, and a web interface for conversation management.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](docker-compose.yml)

## 📋 Table of Contents

- [🚀 Features](#-features)
- [📁 Project Structure](#-project-structure)
- [🛠️ Prerequisites](#️-prerequisites)
- [🚀 Quick Start](#-quick-start)
  - [Option 1: Docker (Recommended)](#option-1-docker-recommended)
  - [Option 2: Local Development](#option-2-local-development)
- [⚙️ Configuration](#️-configuration)
  - [Environment Variables](#environment-variables)
  - [Security Features](#security-features)
  - [Monitoring Features](#monitoring-features)
  - [Available Personas](#available-personas)
  - [TTS Voices](#tts-voices)
- [🌐 API Endpoints](#-api-endpoints)
  - [Web Interface](#web-interface)
  - [RESTful API](#restful-api)
  - [Legacy API Endpoints](#legacy-api-endpoints)
- [🛠️ Development](#️-development)
  - [Project Structure](#project-structure)
  - [Common Commands](#common-commands)
  - [Adding New Features](#adding-new-features)
- [🔧 Troubleshooting](#-troubleshooting)
  - [Common Issues](#common-issues)
  - [Debug Mode](#debug-mode)
- [📚 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [🔒 Security](#-security)
- [🙏 Acknowledgments](#-acknowledgments)

## 🚀 Features

- **Real-time Voice Processing**: Uses WebRTC VAD for voice activity detection and Faster Whisper for speech-to-text
- **Local LLM Integration**: Connects to Ollama for local language model inference
- **Text-to-Speech**: Edge TTS for natural voice synthesis
- **Web Interface**: Flask-based web UI for conversation management and settings
- **Conversation History**: SQLite database for storing and searching conversations
- **Persona System**: Multiple AI personas with different personalities and behaviors
- **Security & Authentication**: JWT-based authentication, password hashing, and data encryption
- **System Monitoring**: Real-time metrics collection, performance tracking, and error logging
- **RESTful API**: Comprehensive API endpoints for external integrations
- **Docker Support**: Complete containerization with Docker and Docker Compose
- **Modular Architecture**: Well-organized, maintainable codebase

## 📁 Project Structure

```
AI Call Bot/
├── src/                    # Python source code
│   ├── main.py            # Main application entry point
│   ├── config.py          # Configuration and constants
│   ├── database.py        # Database operations
│   ├── llm_client.py      # Ollama API integration
│   ├── tts_client.py      # Text-to-speech functionality
│   ├── audio_processor.py # Audio recording and processing
│   ├── conversation_manager.py # Main conversation orchestration
│   ├── web_routes.py      # Flask web routes and API
│   ├── security.py        # Security and authentication system
│   ├── monitoring.py      # System monitoring and metrics
│   ├── api_routes.py      # RESTful API endpoints
│   ├── start.py           # Flexible startup script
│   ├── test_setup.py      # Setup verification script
│   ├── app.py             # Original monolithic app (legacy)
│   ├── mcp_tools.py       # Google Calendar integration
│   ├── oauth_setup.py     # OAuth setup utilities
│   └── sip_llm_bot.py    # Standalone SIP bot
├── docs/                  # Documentation
│   ├── README.md          # Detailed documentation
│   ├── PROJECT_STRUCTURE.md # Project structure details
│   ├── REFACTOR_SUMMARY.md # Refactoring documentation
│   ├── IMPLEMENTATION_GUIDE.md # Implementation guide
│   └── UPGRADES.md        # Upgrade history
├── templates/             # HTML templates
│   ├── index.html         # Main web interface
│   ├── conversation.html  # Conversation view
│   └── settings.html      # Settings page
├── data/                  # Runtime data directory
├── main.py                # Root entry point
├── start.py               # Root startup script
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker build instructions
├── docker-compose.yml    # Multi-service orchestration
├── Makefile              # Development automation
├── .gitignore           # Git ignore rules
├── .dockerignore        # Docker ignore rules
├── env.example          # Environment variables template
├── LICENSE              # MIT License
└── SECURITY.md          # Security policy
```

## 🛠️ Prerequisites

- **Python 3.10+**
- **Ollama** (for local LLM inference)
- **Docker & Docker Compose** (optional, for containerized deployment)
- **Audio hardware** (microphone and speakers)

## 🚀 Quick Start

### Option 1: Docker (Recommended)

1. **Clone and navigate to the project:**
   ```bash
   git clone https://github.com/chartmann1590/AI-Call-Bot.git
   cd AI-Call-Bot
   ```

2. **Start with Docker Compose:**
   ```bash
   make docker-quick
   ```
   or manually:
   ```bash
   docker-compose up -d
   ```

3. **Access the web interface:**
   ```
   http://localhost:5000
   ```

### Option 2: Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/chartmann1590/AI-Call-Bot.git
   cd AI-Call-Bot
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment:**
   ```bash
   cp env.example .env
   # Edit .env with your settings
   ```

5. **Start Ollama:**
   ```bash
   # Install and start Ollama
   # Download a model: ollama pull llama3.2
   ```

6. **Run the application:**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `env.example`:

```env
# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# TTS Configuration
TTS_VOICE=en-US-JennyNeural

# Persona Selection
CURRENT_PERSONA_KEY=helpful

# Flask Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False

# Database
DATABASE_PATH=conversations.db

# Security Configuration
SECRET_KEY=your-secret-key-here
JWT_EXPIRATION_HOURS=24
ENCRYPTION_KEY=your-encryption-key-here

# Audio Settings (optional)
SAMPLE_RATE=16000
FRAME_DURATION_MS=30
SILENCE_THRESHOLD=0.01
HANGUP_TIMEOUT=5.0
```

### Security Features

The system includes comprehensive security features:

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt-based password security
- **Data Encryption**: Fernet encryption for sensitive data
- **Input Sanitization**: Protection against injection attacks
- **Audit Logging**: Complete action tracking and logging
- **Rate Limiting**: Protection against abuse

### Monitoring Features

Real-time system monitoring and metrics:

- **System Metrics**: CPU, memory, disk, and network usage
- **Conversation Metrics**: Active conversations, duration, message counts
- **AI Performance**: LLM response times and success rates
- **Error Tracking**: Centralized error logging and reporting
- **Health Checks**: System health status monitoring

### Available Personas

- `helpful`: Friendly and helpful assistant
- `professional`: Business-oriented responses
- `creative`: Artistic and imaginative responses
- `technical`: Technical and detailed explanations

### TTS Voices

The system supports various Edge TTS voices. Popular options:
- `en-US-JennyNeural` (female)
- `en-US-GuyNeural` (male)
- `en-GB-RyanNeural` (British male)

## 🌐 API Endpoints

### Web Interface
- `GET /` - Main dashboard
- `GET /conversations/<id>` - View specific conversation
- `GET /search` - Search conversations
- `GET /settings` - Settings page
- `POST /settings` - Update settings

### RESTful API
- `GET /api/health` - System health check
- `GET /api/conversations` - List all conversations
- `POST /api/conversations` - Start new conversation
- `GET /api/conversations/<id>` - Get conversation details
- `GET /api/search` - Search conversations
- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings
- `POST /api/llm/query` - Direct LLM interaction
- `POST /api/tts/speak` - Text-to-speech conversion
- `GET /api/metrics` - System metrics and performance data
- `POST /api/auth/login` - User authentication
- `POST /api/auth/logout` - User logout

### Legacy API Endpoints
- `GET /api/status` - Get conversation status
- `POST /api/start_conversation` - Start voice conversation
- `POST /api/stop_conversation` - Stop voice conversation
- `POST /preview_tts` - Preview TTS voice

## 🛠️ Development

### Project Structure

The project follows a modular architecture:

- **`src/`**: All Python source code organized by functionality
- **`docs/`**: Documentation and project files
- **`templates/`**: HTML templates for web interface
- **`data/`**: Runtime data (database, logs)

### Common Commands

```bash
# Development
make install          # Install dependencies
make test            # Run tests
make run             # Run locally
make run-debug       # Run in debug mode

# Docker
make docker-build    # Build Docker image
make docker-run      # Start with Docker Compose
make docker-stop     # Stop Docker services
make docker-logs     # View logs

# Maintenance
make clean           # Clean temporary files
make reset-db        # Reset database
```

### Adding New Features

1. **New Module**: Add to `src/` directory
2. **Configuration**: Update `src/config.py`
3. **Database**: Add to `src/database.py`
4. **Web Routes**: Add to `src/web_routes.py`
5. **Security**: Integrate with `src/security.py` for authentication
6. **Monitoring**: Add metrics to `src/monitoring.py`
7. **API Routes**: Add RESTful endpoints to `src/api_routes.py`
8. **Documentation**: Update `docs/README.md`

## 🔧 Troubleshooting

### Common Issues

1. **Ollama Connection Failed**
   - Ensure Ollama is running: `ollama serve`
   - Check URL in `.env`: `OLLAMA_URL=http://localhost:11434`
   - Verify model is downloaded: `ollama list`

2. **Audio Issues**
   - Check microphone permissions
   - Verify audio device selection
   - Test with: `python src/test_setup.py`

3. **Docker Audio Problems**
   - Ensure audio group access: `--group-add audio`
   - Check device passthrough in `docker-compose.yml`

4. **Database Errors**
   - Reset database: `make reset-db`
   - Check file permissions for `data/` directory

### Debug Mode

Enable debug mode for detailed logging:

```bash
FLASK_DEBUG=True python main.py
```

## 📚 Documentation

For detailed documentation, see the [`docs/`](docs/) directory:

- [📖 Detailed Documentation](docs/README.md) - Comprehensive project documentation
- [🏗️ Project Structure](docs/PROJECT_STRUCTURE.md) - Detailed project structure
- [🔄 Refactor Summary](docs/REFACTOR_SUMMARY.md) - Refactoring documentation
- [📋 Implementation Guide](docs/IMPLEMENTATION_GUIDE.md) - Implementation details
- [⬆️ Upgrades](docs/UPGRADES.md) - Upgrade history and changes

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔒 Security

For security concerns, please see our [Security Policy](SECURITY.md) or contact us directly.

## 🙏 Acknowledgments

- **Ollama** for local LLM inference
- **Edge TTS** for text-to-speech
- **Faster Whisper** for speech recognition
- **WebRTC VAD** for voice activity detection
- **Flask** for web framework
- **Docker** for containerization
- **SQLite** for database management

---

**Made with ❤️ by the AI Call Bot Team** 