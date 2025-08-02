"""
Conversation Manager module for AI Call Bot application.
Handles the main conversation loop and coordinates between audio, LLM, and TTS components.
"""

import threading
import time
import os
from typing import Optional
import pygame

from audio_processor import audio_processor
from llm_client import query_ollama
from tts_client import speak_text, cleanup_audio_file
from database import (
    start_new_conversation, insert_message, 
    generate_and_store_summary, get_conversation_text
)
from config import CONFIRM_TIMEOUT_SECONDS

class ConversationManager:
    """Manages the main conversation loop and coordinates all components."""
    
    def __init__(self):
        self.current_conversation_id: Optional[int] = None
        self.is_active = False
        self.confirmation_pending = False
        self.last_speech_time = time.time()
        
    def start_conversation(self):
        """Start a new conversation."""
        self.current_conversation_id = start_new_conversation()
        self.is_active = True
        self.confirmation_pending = False
        self.last_speech_time = time.time()
        
        print(f"[INFO] Started conversation #{self.current_conversation_id}")
        
        # Start the audio processing in a separate thread
        audio_thread = threading.Thread(
            target=self._audio_loop,
            daemon=True
        )
        audio_thread.start()
    
    def stop_conversation(self):
        """Stop the current conversation."""
        if self.current_conversation_id:
            # Generate summary for the conversation
            try:
                generate_and_store_summary(self.current_conversation_id)
                print(f"[INFO] Conversation #{self.current_conversation_id} ended and summarized.")
            except Exception as e:
                print(f"[ERROR] Failed to generate summary: {e}")
        
        self.current_conversation_id = None
        
        # Start a new conversation automatically for continuous listening
        if self.is_active:
            print("[INFO] Starting new conversation for continuous listening...")
            self.start_conversation()
    
    def _audio_loop(self):
        """Main audio processing loop."""
        def on_transcription(text: str):
            """Handle transcribed text from user."""
            if not self.is_active or not text.strip():
                print(f"[DEBUG] ⚠️ Skipping empty transcription or inactive conversation")
                return
            
            print(f"[USER] 🗣️ '{text}'")
            print(f"[DEBUG] 📝 Storing user message in database...")
            
            # Store user message
            if self.current_conversation_id:
                insert_message(self.current_conversation_id, "user", text)
                print(f"[DEBUG] ✅ User message stored in conversation #{self.current_conversation_id}")
            
            # Get AI response
            print(f"[DEBUG] 🤖 Sending to Ollama at {os.getenv('OLLAMA_URL', 'http://localhost:11434')}...")
            try:
                response = query_ollama(text)
                print(f"[AI] 🤖 '{response}'")
                print(f"[DEBUG] ✅ Ollama response received")
                
                # Store AI response
                if self.current_conversation_id:
                    print(f"[DEBUG] 📝 Storing AI response in database...")
                    insert_message(self.current_conversation_id, "assistant", response)
                    print(f"[DEBUG] ✅ AI response stored in conversation #{self.current_conversation_id}")
                
                # Speak the response
                print(f"[DEBUG] 🔊 Starting TTS playback...")
                self._speak_response(response)
                
            except Exception as e:
                print(f"[ERROR] ❌ Failed to get AI response: {e}")
                error_msg = "I'm sorry, I'm having trouble processing your request right now."
                print(f"[DEBUG] 🔊 Playing error message via TTS...")
                self._speak_response(error_msg)
        
        def on_silence():
            """Handle silence detection."""
            if self.confirmation_pending:
                # If we're waiting for confirmation and silence continues, end conversation
                print("[INFO] No response to confirmation, ending conversation.")
                self.stop_conversation()
            else:
                # Just continue listening for new speech
                pass
        
        def on_hangup():
            """Handle hangup timeout."""
            if not self.confirmation_pending:
                # Ask if user is still there
                confirmation_msg = "Are you still there? I haven't heard from you in a while."
                print(f"[AI] {confirmation_msg}")
                
                # Store confirmation message
                if self.current_conversation_id:
                    insert_message(self.current_conversation_id, "assistant", confirmation_msg)
                
                # Speak confirmation
                self._speak_response(confirmation_msg)
                
                # Set confirmation pending
                self.confirmation_pending = True
                self.last_speech_time = time.time()
                
                # Start a timer to end conversation if no response
                def confirmation_timer():
                    time.sleep(CONFIRM_TIMEOUT_SECONDS)
                    if self.confirmation_pending:
                        print("[INFO] No response to confirmation, ending conversation.")
                        self.stop_conversation()
                
                threading.Thread(target=confirmation_timer, daemon=True).start()
        
        # Start audio processing
        audio_processor.listen_and_transcribe(on_transcription, on_silence, on_hangup)
    
    def _speak_response(self, text: str):
        """Speak the AI response using TTS."""
        try:
            print(f"[DEBUG] 🔊 Setting TTS playing flag...")
            # Set TTS playing flag
            audio_processor.set_tts_playing(True)
            
            # Generate speech
            print(f"[DEBUG] 🔊 Calling speak_text()...")
            audio_file = speak_text(text)
            print(f"[DEBUG] 🔊 Audio file generated: {audio_file}")
            
            # Play the audio with pygame
            print(f"[DEBUG] 🔊 Playing audio with pygame...")
            pygame.mixer.init()
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            
            print(f"[DEBUG] 🔊 Audio playback completed")
            
            # Clean up the audio file
            print(f"[DEBUG] 🧹 Scheduling audio file cleanup...")
            cleanup_audio_file(audio_file)
            
        except Exception as e:
            print(f"[ERROR] ❌ TTS failed: {e}")
        finally:
            # Clear TTS playing flag
            print(f"[DEBUG] 🔊 Clearing TTS playing flag...")
            audio_processor.set_tts_playing(False)
    
    def get_conversation_status(self) -> dict:
        """Get current conversation status."""
        return {
            "is_active": self.is_active,
            "conversation_id": self.current_conversation_id,
            "confirmation_pending": self.confirmation_pending,
            "time_since_last_speech": time.time() - self.last_speech_time
        }

# Global conversation manager instance
conversation_manager = ConversationManager() 