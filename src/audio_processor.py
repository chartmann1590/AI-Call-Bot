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
    SAMPLE_RATE, FRAME_SIZE, FRAME_DURATION_MS, AGGRESSIVENESS, AMPLITUDE_THRESHOLD,
    SILENCE_THRESHOLD_FRAMES, MIN_UTTERANCE_FRAMES, EXTRA_FRAMES,
    HANGUP_TIMEOUT_SECONDS, CONFIRM_TIMEOUT_SECONDS
)

class AudioProcessor:
    """Handles audio recording, VAD, and transcription."""
    
    def __init__(self):
        self.vad = webrtcvad.Vad(AGGRESSIVENESS)
        self.whisper_model: Optional[WhisperModel] = None
        self.tts_playing = threading.Event()
        self.is_processing = threading.Event()  # Flag to track when processing audio
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
            nonlocal silent_frames, last_speech_time
            
            if status:
                print(f"[AUDIO] Status: {status}")
            
            # Convert to int16 for VAD
            audio_data = (indata[:, 0] * 32767).astype(np.int16)
            
            # Calculate amplitude for debugging
            amplitude = np.max(np.abs(audio_data))
            
            # Check amplitude threshold
            if amplitude < AMPLITUDE_THRESHOLD:
                silent_frames += 1
                return
            
            # Debug: Show when we have audio above threshold
            print(f"[DEBUG] 🔊 Audio above threshold! Amplitude: {amplitude} (threshold: {AMPLITUDE_THRESHOLD})")
            
            # VAD processing
            is_speech = self.vad.is_speech(audio_data.tobytes(), SAMPLE_RATE)
            
            if is_speech:
                print(f"[DEBUG] 🎤 Speech detected! Amplitude: {amplitude}, Frames: {len(frames)}")
                frames.append(audio_data.copy())
                silent_frames = 0
                last_speech_time = time.time()
            else:
                silent_frames += 1
                print(f"[DEBUG] 🔊 Audio detected but not speech. Amplitude: {amplitude}, Silent frames: {silent_frames}")
                
                # If we have enough frames and silence threshold reached, OR if we have a moderate amount of speech
                if (len(frames) >= MIN_UTTERANCE_FRAMES and 
                    (silent_frames >= SILENCE_THRESHOLD_FRAMES or len(frames) >= 20)):
                     
                     print(f"[DEBUG] 🎵 Processing audio after silence! Frames: {len(frames)}, Silent frames: {silent_frames}")
                     
                     # Calculate duration of speech (frames * frame_duration)
                     speech_duration_ms = len(frames) * FRAME_DURATION_MS
                     print(f"[DEBUG] 🎵 Speech duration: {speech_duration_ms}ms")
                     
                     # Only process if we have at least 0.1 seconds of speech
                     if speech_duration_ms >= 100:
                         # Add extra frames to catch trailing words
                         extra_frames_to_add = min(EXTRA_FRAMES, len(frames))
                         if extra_frames_to_add > 0:
                             frames.extend(frames[-extra_frames_to_add:])
                         
                         # Process the audio
                         self._process_audio_frames(frames, on_transcription)
                         frames.clear()
                         silent_frames = 0
                     else:
                         print(f"[DEBUG] ⚠️ Speech too short ({speech_duration_ms}ms), ignoring")
                         frames.clear()
                         silent_frames = 0
            
            # Check for hangup timeout (but not during processing)
            if (time.time() - last_speech_time > HANGUP_TIMEOUT_SECONDS and 
                not self.is_processing.is_set()):
                print(f"[DEBUG] ⏰ Hangup timeout reached ({HANGUP_TIMEOUT_SECONDS}s)")
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
                    
                    # Check for hangup timeout (but not during processing)
                    if (time.time() - last_speech_time > HANGUP_TIMEOUT_SECONDS and 
                        not self.is_processing.is_set()):
                        print(f"[DEBUG] ⏰ Main loop: Hangup timeout reached ({HANGUP_TIMEOUT_SECONDS}s)")
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
        
        print(f"[DEBUG] 🎵 Starting audio processing... Frames: {len(frames)}")
        
        # Set processing flag to prevent hangup during transcription
        self.is_processing.set()
        print(f"[DEBUG] 🔒 Processing flag set - hangup timeout disabled")
        
        try:
            # Concatenate all frames
            print(f"[DEBUG] 🔗 Concatenating {len(frames)} audio frames...")
            audio_data = np.concatenate(frames)
            print(f"[DEBUG] ✅ Audio concatenated. Total samples: {len(audio_data)}")
            
            # Save to temporary file
            print(f"[DEBUG] 💾 Saving audio to temp_audio.wav...")
            with sf.SoundFile('temp_audio.wav', 'w', samplerate=SAMPLE_RATE, 
                            channels=1, subtype='PCM_16') as f:
                f.write(audio_data)
            print(f"[DEBUG] ✅ Audio saved to temp_audio.wav")
            
            # Transcribe with Whisper
            print(f"[DEBUG] 🎤 Starting Whisper transcription...")
            segments, _ = self.whisper_model.transcribe('temp_audio.wav', language='en')
            
            # Convert generator to list and combine all segments
            segments_list = list(segments)
            transcription = ' '.join([segment.text for segment in segments_list]).strip()
            print(f"[DEBUG] 🎤 Whisper segments: {len(segments_list)}")
            
            if transcription:
                print(f"[TRANSCRIPTION] 🎤 '{transcription}'")
                print(f"[DEBUG] 📞 Calling on_transcription callback...")
                on_transcription(transcription)
            else:
                print(f"[DEBUG] ⚠️ No transcription generated")
            
            # Clean up temp file
            import os
            if os.path.exists('temp_audio.wav'):
                os.remove('temp_audio.wav')
                print(f"[DEBUG] 🧹 Cleaned up temp_audio.wav")
                
        except Exception as e:
            print(f"[ERROR] ❌ Transcription failed: {e}")
        finally:
            # Clear processing flag
            self.is_processing.clear()
            print(f"[DEBUG] 🔓 Processing flag cleared - hangup timeout re-enabled")
    
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