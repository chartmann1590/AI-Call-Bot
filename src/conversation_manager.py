"""
Conversation Manager module for AI Call Bot application.
Handles the main conversation loop and coordinates between audio, LLM, and TTS components.
"""

import threading
import time
from typing import Optional
from playsound import playsound

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
        self.is_active = False
        audio_processor.stop_listening()
        
        if self.current_conversation_id:
            # Generate summary for the conversation
            try:
                generate_and_store_summary(self.current_conversation_id)
                print(f"[INFO] Conversation #{self.current_conversation_id} ended and summarized.")
            except Exception as e:
                print(f"[ERROR] Failed to generate summary: {e}")
        
        self.current_conversation_id = None
    
    def _audio_loop(self):
        """Main audio processing loop."""
        def on_transcription(text: str):
            """Handle transcribed text from user."""
            if not self.is_active or not text.strip():
                return
            
            print(f"[USER] {text}")
            
            # Store user message
            if self.current_conversation_id:
                insert_message(self.current_conversation_id, "user", text)
            
            # Get AI response
            try:
                response = query_ollama(text)
                print(f"[AI] {response}")
                
                # Store AI response
                if self.current_conversation_id:
                    insert_message(self.current_conversation_id, "assistant", response)
                
                # Speak the response
                self._speak_response(response)
                
            except Exception as e:
                print(f"[ERROR] Failed to get AI response: {e}")
                error_msg = "I'm sorry, I'm having trouble processing your request right now."
                self._speak_response(error_msg)
        
        def on_silence():
            """Handle silence detection."""
            if self.confirmation_pending:
                # If we're waiting for confirmation and silence continues, end conversation
                print("[INFO] No response to confirmation, ending conversation.")
                self.stop_conversation()
        
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
            # Set TTS playing flag
            audio_processor.set_tts_playing(True)
            
            # Generate speech
            audio_file = speak_text(text)
            
            # Play the audio
            playsound(audio_file)
            
            # Clean up the audio file
            cleanup_audio_file(audio_file)
            
        except Exception as e:
            print(f"[ERROR] TTS failed: {e}")
        finally:
            # Clear TTS playing flag
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