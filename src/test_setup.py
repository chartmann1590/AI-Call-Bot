#!/usr/bin/env python3
"""
Test script for AI Call Bot application.
Verifies that all components are working correctly.
"""

import sys
import os
import requests
import sqlite3
from dotenv import load_dotenv

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import config
        print("✓ Config module imported")
    except ImportError as e:
        print(f"✗ Config module failed: {e}")
        return False
    
    try:
        import database
        print("✓ Database module imported")
    except ImportError as e:
        print(f"✗ Database module failed: {e}")
        return False
    
    try:
        import llm_client
        print("✓ LLM client module imported")
    except ImportError as e:
        print(f"✗ LLM client module failed: {e}")
        return False
    
    try:
        import tts_client
        print("✓ TTS client module imported")
    except ImportError as e:
        print(f"✗ TTS client module failed: {e}")
        return False
    
    try:
        import audio_processor
        print("✓ Audio processor module imported")
    except ImportError as e:
        print(f"✗ Audio processor module failed: {e}")
        return False
    
    try:
        import conversation_manager
        print("✓ Conversation manager module imported")
    except ImportError as e:
        print(f"✗ Conversation manager module failed: {e}")
        return False
    
    try:
        import web_routes
        print("✓ Web routes module imported")
    except ImportError as e:
        print(f"✗ Web routes module failed: {e}")
        return False
    
    return True

def test_database():
    """Test database initialization."""
    print("\nTesting database...")
    
    try:
        from database import init_db, get_db
        init_db()
        db = get_db()
        db.execute("SELECT 1")
        print("✓ Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_ollama_connection():
    """Test Ollama connection."""
    print("\nTesting Ollama connection...")
    
    try:
        from config import OLLAMA_URL
        from llm_client import test_ollama_connection
        
        if test_ollama_connection():
            print(f"✓ Ollama connection successful at {OLLAMA_URL}")
            return True
        else:
            print(f"✗ Ollama connection failed at {OLLAMA_URL}")
            print("  Make sure Ollama is running and accessible")
            return False
    except Exception as e:
        print(f"✗ Ollama test failed: {e}")
        return False

def test_tts():
    """Test TTS functionality."""
    print("\nTesting TTS...")
    
    try:
        from tts_client import speak_text, cleanup_audio_file
        from config import TTS_VOICE
        
        # Test TTS generation
        audio_file = speak_text("Test message", TTS_VOICE)
        if os.path.exists(audio_file):
            print(f"✓ TTS generation successful with voice {TTS_VOICE}")
            cleanup_audio_file(audio_file)
            return True
        else:
            print("✗ TTS generation failed")
            return False
    except Exception as e:
        print(f"✗ TTS test failed: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from config import (
            OLLAMA_URL, OLLAMA_MODEL, TTS_VOICE, 
            CURRENT_PERSONA_KEY, PERSONAS, VOICE_OPTIONS
        )
        
        print(f"✓ Ollama URL: {OLLAMA_URL}")
        print(f"✓ Ollama Model: {OLLAMA_MODEL}")
        print(f"✓ TTS Voice: {TTS_VOICE}")
        print(f"✓ Current Persona: {CURRENT_PERSONA_KEY}")
        print(f"✓ Available Personas: {len(PERSONAS)}")
        print(f"✓ Available Voices: {len(VOICE_OPTIONS)}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("AI Call Bot Setup Test")
    print("=" * 50)
    
    # Load environment
    load_dotenv()
    
    tests = [
        test_imports,
        test_config,
        test_database,
        test_ollama_connection,
        test_tts
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! The application should work correctly.")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 