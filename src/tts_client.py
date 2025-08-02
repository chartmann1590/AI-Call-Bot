"""
TTS Client module for AI Call Bot application.
Handles all text-to-speech operations using Edge TTS.
"""

import asyncio
import tempfile
import os
import time
import threading
from typing import Optional
import edge_tts
from config import TTS_VOICE

async def _edge_tts_generate(text: str, voice: str, output_path: str):
    """
    Generate speech using Edge TTS and save to file.
    
    Args:
        text: Text to convert to speech
        voice: Voice identifier (e.g., "en-US-JennyNeural")
        output_path: Path where the audio file should be saved
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def speak_text(text: str, voice: Optional[str] = None) -> str:
    """
    Convert text to speech and return the path to the audio file.
    
    Args:
        text: Text to convert to speech
        voice: Optional voice identifier (defaults to TTS_VOICE)
    
    Returns:
        Path to the generated audio file
    """
    if voice is None:
        voice = TTS_VOICE
    
    print(f"[DEBUG] 🎵 TTS: Converting '{text[:50]}{'...' if len(text) > 50 else ''}' to speech")
    print(f"[DEBUG] 🎵 TTS: Using voice '{voice}'")
    
    # Create a temporary file for the audio
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        temp_path = tmp.name
    
    print(f"[DEBUG] 🎵 TTS: Created temp file: {temp_path}")
    
    try:
        # Generate the speech (blocking call via asyncio.run)
        print(f"[DEBUG] 🎵 TTS: Generating speech with Edge TTS...")
        asyncio.run(_edge_tts_generate(text, voice, temp_path))
        print(f"[DEBUG] 🎵 TTS: Speech generated successfully")
        return temp_path
    except Exception as e:
        print(f"[ERROR] ❌ TTS generation failed: {e}")
        # Clean up the temp file if it was created
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

def preview_voice(text: str, voice: str) -> str:
    """
    Generate a preview of a voice with given text.
    
    Args:
        text: Text to convert to speech
        voice: Voice identifier
    
    Returns:
        Path to the generated audio file
    """
    return speak_text(text, voice)

def cleanup_audio_file(file_path: str, delay_seconds: int = 1):
    """
    Clean up an audio file after a delay.
    
    Args:
        file_path: Path to the audio file to delete
        delay_seconds: Number of seconds to wait before deletion
    """
    def cleanup():
        time.sleep(delay_seconds)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"[WARNING] Failed to cleanup audio file {file_path}: {e}")
    
    # Run cleanup in a separate thread
    threading.Thread(target=cleanup, daemon=True).start()

def get_available_voices() -> list:
    """
    Get list of available Edge TTS voices.
    
    Returns:
        List of voice identifiers
    """
    try:
        # This would require an async function to get voices from edge-tts
        # For now, we'll return a subset of common voices
        return [
            "en-US-JennyNeural",
            "en-US-GuyNeural", 
            "en-GB-SoniaNeural",
            "en-GB-RyanNeural",
            "en-AU-NatashaNeural",
            "en-CA-ClaraNeural"
        ]
    except Exception as e:
        print(f"[ERROR] Failed to get available voices: {e}")
        return ["en-US-JennyNeural"]  # Fallback to default voice 