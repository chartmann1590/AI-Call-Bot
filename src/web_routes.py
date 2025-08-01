"""
Web Routes module for AI Call Bot application.
Handles all Flask routes and web interface functionality.
"""

import datetime
import tempfile
import time
import threading
from flask import Flask, render_template, g, request, jsonify, send_file
from config import VOICE_OPTIONS, PERSONAS, OLLAMA_URL, OLLAMA_MODEL, TTS_VOICE, CURRENT_PERSONA_KEY
from database import (
    get_db, close_db, init_db, get_all_conversations, get_conversation_metadata,
    get_conversation_messages, search_conversations
)
from llm_client import get_available_models
from tts_client import speak_text, cleanup_audio_file
import asyncio
import os

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Register database close function
    app.teardown_appcontext(close_db)
    
    return app

app = create_app()

@app.route("/")
def index():
    """List all conversations (ordered by start_time descending), including short summary."""
    conversations = get_all_conversations()
    return render_template("index.html", conversations=conversations)

@app.route("/conversations/<int:conv_id>")
def view_conversation(conv_id):
    """Show all messages for a given conversation."""
    # Get conversation metadata
    metadata = get_conversation_metadata(conv_id)
    if not metadata:
        return f"Conversation #{conv_id} not found.", 404
    
    # Get conversation messages
    messages = get_conversation_messages(conv_id)
    
    # Organize messages by date
    grouped = {}
    for msg in messages:
        ts = datetime.datetime.fromisoformat(msg["timestamp"])
        date_str = ts.date().isoformat()
        if date_str not in grouped:
            grouped[date_str] = []
        grouped[date_str].append({
            "sender": msg["sender"],
            "text": msg["text"],
            "time": ts.strftime("%H:%M:%S")
        })
    
    # Format persona label
    persona_label = metadata["persona_key"].replace("_", " ").title()
    
    return render_template(
        "conversation.html",
        conversation_id=conv_id,
        start_time=metadata["start_time"],
        llm_model=metadata["llm_model"],
        tts_voice=metadata["tts_voice"],
        persona_label=persona_label,
        full_summary=metadata["summary_full"],
        grouped=grouped
    )

@app.route("/search", methods=["GET"])
def search():
    """Search endpoint for conversations."""
    q = request.args.get("q", "").strip()
    try:
        threshold = float(request.args.get("threshold", "0.5"))
    except ValueError:
        threshold = 0.5

    if not q:
        return jsonify([])

    results = search_conversations(q, threshold)
    return jsonify(results)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    """Display and process settings page."""
    global OLLAMA_URL, OLLAMA_MODEL, TTS_VOICE, CURRENT_PERSONA_KEY

    # On POST, update the globals
    if request.method == "POST":
        new_url = request.form.get("ollama_url", "").strip()
        new_model = request.form.get("ollama_model", "").strip()
        new_voice = request.form.get("tts_voice", "").strip()
        new_persona = request.form.get("persona_key", "").strip()

        if new_url:
            OLLAMA_URL = new_url
        if new_model:
            OLLAMA_MODEL = new_model
        if new_voice:
            TTS_VOICE = new_voice
        if new_persona in PERSONAS:
            CURRENT_PERSONA_KEY = new_persona

    # Fetch available models from the current OLLAMA_URL
    try:
        model_names = get_available_models()
    except Exception:
        model_names = []

    # Build a list of (key, label) for persona dropdown
    persona_options = [(key, key.replace("_", " ").title()) for key in PERSONAS]

    # Render settings page with current values + available options
    return render_template(
        "settings.html",
        ollama_url=OLLAMA_URL,
        model_names=model_names,
        current_model=OLLAMA_MODEL or "llama3.2",
        voices=VOICE_OPTIONS,
        current_voice=TTS_VOICE or "en-US-JennyNeural",
        personas=persona_options,
        current_persona=CURRENT_PERSONA_KEY
    )

@app.route("/preview_tts", methods=["GET"])
def preview_tts():
    """Generate a short sample using Edge-TTS with the selected voice code."""
    voice = request.args.get("voice", "").strip()
    if not voice:
        voice = "en-US-JennyNeural"

    # Generate a short preview phrase
    text = "This is a preview of the selected voice."

    # Create a temporary file for the MP3
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Generate the MP3
        audio_file = speak_text(text, voice)
        
        # Send the file back to the browser
        return send_file(audio_file, mimetype="audio/mpeg", as_attachment=False)
    except Exception as e:
        print(f"[PREVIEW-TTS][ERROR] {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return ("", 500)
    finally:
        # Clean up: remove temp file after a short delay
        def cleanup_file(path):
            time.sleep(1)
            if os.path.exists(path):
                os.remove(path)
        threading.Thread(target=cleanup_file, args=(audio_file,), daemon=True).start()

@app.route("/api/status")
def api_status():
    """API endpoint to get application status."""
    from conversation_manager import conversation_manager
    
    status = conversation_manager.get_conversation_status()
    return jsonify(status)

@app.route("/api/start_conversation", methods=["POST"])
def api_start_conversation():
    """API endpoint to start a new conversation."""
    from conversation_manager import conversation_manager
    
    if conversation_manager.is_active:
        return jsonify({"error": "Conversation already active"}), 400
    
    conversation_manager.start_conversation()
    return jsonify({"success": True, "conversation_id": conversation_manager.current_conversation_id})

@app.route("/api/stop_conversation", methods=["POST"])
def api_stop_conversation():
    """API endpoint to stop the current conversation."""
    from conversation_manager import conversation_manager
    
    if not conversation_manager.is_active:
        return jsonify({"error": "No active conversation"}), 400
    
    conversation_manager.stop_conversation()
    return jsonify({"success": True}) 