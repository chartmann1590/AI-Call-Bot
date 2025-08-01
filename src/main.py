"""
Main application entry point for AI Call Bot.
Ties together all modules and starts the Flask server.
"""

import threading
import os
import sys
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import modules
from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG
from database import init_db
from web_routes import app
from conversation_manager import conversation_manager

def main():
    """Main application entry point."""
    print("[INFO] Starting AI Call Bot application...")
    
    # Initialize database
    print("[INFO] Initializing database...")
    init_db()
    print("[INFO] Database initialized.")
    
    # Initialize audio processor
    print("[INFO] Initializing audio processor...")
    from audio_processor import audio_processor
    audio_processor.initialize_whisper()
    print("[INFO] Audio processor initialized.")
    
    # Start the Flask application
    print(f"[INFO] Starting Flask server on {FLASK_HOST}:{FLASK_PORT}")
    print(f"[INFO] Debug mode: {FLASK_DEBUG}")
    print(f"[INFO] Web interface available at: http://{FLASK_HOST}:{FLASK_PORT}")
    
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
        use_reloader=False  # Disable reloader to avoid duplicate threads
    )

if __name__ == "__main__":
    main() 