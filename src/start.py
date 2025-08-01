#!/usr/bin/env python3
"""
Startup script for AI Call Bot application.
Provides easy configuration and startup options.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

def main():
    """Main startup function."""
    parser = argparse.ArgumentParser(description='AI Call Bot Startup')
    parser.add_argument('--env', default='.env', help='Environment file path')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--ollama-url', help='Ollama server URL')
    parser.add_argument('--model', help='Ollama model to use')
    parser.add_argument('--voice', help='TTS voice to use')
    parser.add_argument('--persona', help='Persona to use')
    
    args = parser.parse_args()
    
    # Load environment file
    if os.path.exists(args.env):
        load_dotenv(args.env)
        print(f"[INFO] Loaded environment from {args.env}")
    
    # Override with command line arguments
    if args.debug:
        os.environ['FLASK_DEBUG'] = 'True'
    if args.port:
        os.environ['FLASK_PORT'] = str(args.port)
    if args.host:
        os.environ['FLASK_HOST'] = args.host
    if args.ollama_url:
        os.environ['OLLAMA_URL'] = args.ollama_url
    if args.model:
        os.environ['OLLAMA_MODEL'] = args.model
    if args.voice:
        os.environ['TTS_VOICE'] = args.voice
    if args.persona:
        os.environ['CURRENT_PERSONA_KEY'] = args.persona
    
    # Import and run main application
    from .main import main as app_main
    app_main()

if __name__ == "__main__":
    main() 