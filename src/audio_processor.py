"""
Audio Processor module for AI Call Bot application.
Handles voice activity detection, audio recording, and transcription using Whisper.
"""

import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad
import threading
import time
from typing import Optional, Callable
from faster_whisper import WhisperModel
from config import (
    SAMPLE_RATE, FRAME_SIZE, AGGRESSIVENESS, AMPLITUDE_THRESHOLD,
    SILENCE_THRESHOLD_FRAMES, MIN_UTTERANCE_FRAMES, EXTRA_FRAMES,
    HANGUP_TIMEOUT_SECONDS, CONFIRM_TIMEOUT_SECONDS
)

class AudioProcessor:
    """Handles audio recording, VAD, and transcription."""
    
    def __init__(self):
        self.vad = webrtcvad.Vad(AGGRESSIVENESS)
        self.whisper_model: Optional[WhisperModel] = None
        self.tts_playing = threading.Event()
        self.is_listening = False
        self.current_conversation_id: Optional[int] = None
        
    def initialize_whisper(self):
        """Initialize the Whisper model for transcription."""
        if self.whisper_model is None:
            print("[INFO] Loading Whisper model (base)…")
            self.whisper_model = WhisperModel("base", device="cpu")
            print("[INFO] Whisper model loaded.")
    
    def listen_and_transcribe(self, 
                            on_transcription: Callable[[str], None],
                            on_silence: Callable[[], None],
                            on_hangup: Callable[[], None]) -> None:
        """
        Main audio processing loop with VAD and transcription.
        
        Args:
            on_transcription: Callback function called with transcribed text
            on_silence: Callback function called when silence is detected
            on_hangup: Callback function called when hangup timeout is reached
        """
        self.is_listening = True
        
        # Initialize Whisper if not already done
        self.initialize_whisper()
        
        # Audio recording setup
        frames = []
        silent_frames = 0
        last_speech_time = time.time()
        
        def audio_callback(indata, frames_count, time_info, status):
            if status:
                print(f"[AUDIO] Status: {status}")
            
            # Convert to int16 for VAD
            audio_data = (indata[:, 0] * 32767).astype(np.int16)
            
            # Check amplitude threshold
            if np.max(np.abs(audio_data)) < AMPLITUDE_THRESHOLD:
                return
            
            # VAD processing
            is_speech = self.vad.is_speech(audio_data.tobytes(), SAMPLE_RATE)
            
            if is_speech:
                frames.append(audio_data.copy())
                silent_frames = 0
                last_speech_time = time.time()
            else:
                silent_frames += 1
                
                # If we have enough frames and silence threshold reached
                if (len(frames) >= MIN_UTTERANCE_FRAMES and 
                    silent_frames >= SILENCE_THRESHOLD_FRAMES):
                    
                    # Add extra frames to catch trailing words
                    extra_frames_to_add = min(EXTRA_FRAMES, len(frames))
                    if extra_frames_to_add > 0:
                        frames.extend(frames[-extra_frames_to_add:])
                    
                    # Process the audio
                    self._process_audio_frames(frames, on_transcription)
                    frames.clear()
                    silent_frames = 0
            
            # Check for hangup timeout
            if time.time() - last_speech_time > HANGUP_TIMEOUT_SECONDS:
                on_hangup()
                return
        
        try:
            with sd.InputStream(
                channels=1,
                samplerate=SAMPLE_RATE,
                blocksize=FRAME_SIZE,
                callback=audio_callback,
                dtype=np.float32
            ):
                print("[INFO] Audio recording started. Speak now...")
                
                while self.is_listening:
                    time.sleep(0.1)
                    
                    # Check for hangup timeout
                    if time.time() - last_speech_time > HANGUP_TIMEOUT_SECONDS:
                        on_hangup()
                        break
                        
        except Exception as e:
            print(f"[ERROR] Audio recording failed: {e}")
        finally:
            self.is_listening = False
    
    def _process_audio_frames(self, frames: list, on_transcription: Callable[[str], None]):
        """Process audio frames and transcribe them."""
        if not frames:
            return
        
        try:
            # Concatenate all frames
            audio_data = np.concatenate(frames)
            
            # Save to temporary file
            with sf.SoundFile('temp_audio.wav', 'w', samplerate=SAMPLE_RATE, 
                            channels=1, subtype='PCM_16') as f:
                f.write(audio_data)
            
            # Transcribe with Whisper
            segments, _ = self.whisper_model.transcribe('temp_audio.wav', language='en')
            
            # Combine all segments
            transcription = ' '.join([segment.text for segment in segments]).strip()
            
            if transcription:
                print(f"[TRANSCRIPTION] {transcription}")
                on_transcription(transcription)
            
            # Clean up temp file
            import os
            if os.path.exists('temp_audio.wav'):
                os.remove('temp_audio.wav')
                
        except Exception as e:
            print(f"[ERROR] Transcription failed: {e}")
    
    def stop_listening(self):
        """Stop the audio listening loop."""
        self.is_listening = False
    
    def set_tts_playing(self, is_playing: bool):
        """Set whether TTS is currently playing."""
        if is_playing:
            self.tts_playing.set()
        else:
            self.tts_playing.clear()
    
    def is_tts_playing(self) -> bool:
        """Check if TTS is currently playing."""
        return self.tts_playing.is_set()

# Global audio processor instance
audio_processor = AudioProcessor() 