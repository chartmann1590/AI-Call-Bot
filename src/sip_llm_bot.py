import os
import tempfile
import threading
import time
import asyncio

import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad
import requests
import edge_tts
from playsound import playsound
from faster_whisper import WhisperModel

# ——————————— CONFIGURATION ———————————

# 1. Audio params (VAD)
SAMPLE_RATE            = 16000        # 16 kHz required by webrtcvad + Whisper
FRAME_DURATION_MS      = 30           # 30 ms per frame for VAD
FRAME_SIZE             = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)  # = 480 samples
AGGRESSIVENESS         = 2            # webrtcvad aggressiveness: 0–3

# 2. Amplitude threshold to filter out low-level noise
AMPLITUDE_THRESHOLD    = 500          # int16 max amplitude threshold

# 3. Ollama HTTP endpoint
OLLAMA_URL             = "http://74.76.44.128:11434"
OLLAMA_MODEL           = None         # will be set at runtime

# 4. Silence detection: how many consecutive silent frames end an utterance
SILENCE_THRESHOLD_FRAMES = 20         # 20 × 30 ms = 600 ms of continuous silence

# 5. Minimum utterance length before we attempt to end it
MIN_UTTERANCE_FRAMES    = 20          # 20 × 30 ms = 600 ms of actual speech

# 6. Extra frames to grab after VAD signals end (to catch trailing words)
EXTRA_FRAMES            = 7           # 7 × 30 ms ≈ 210 ms

# 7. System prompt for Ollama
SYSTEM_INSTRUCTION     = (
    "You are a cheerful, young woman fluent in English, "
    "speaking with a gentle accent. Always respond kindly in English, "
    "providing clear, polite, and helpful answers."
)

# ————— GLOBAL OBJECTS —————

vad             = webrtcvad.Vad(AGGRESSIVENESS)
whisper_model   = None

# When Edge-TTS is speaking, we set this so VAD stops listening
tts_playing     = threading.Event()

# After voice selection, this will hold the Edge-TTS voice name
TTS_VOICE       = None


# ————— SELECT OLLAMA MODEL —————

def select_ollama_model():
    """
    Queries Ollama for available local models (GET /api/tags),
    lists them with indices, and prompts the user to choose one.
    Sets the global OLLAMA_MODEL accordingly.
    """
    global OLLAMA_MODEL
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        tags = data.get("models", [])
    except Exception as e:
        print(f"[ERROR] Could not fetch Ollama models: {e}")
        tags = []

    if not isinstance(tags, list) or not tags:
        print("[WARN] No models returned from Ollama. Using default 'llama3.2:latest'.")
        OLLAMA_MODEL = "llama3.2:latest"
        return

    print("\nAvailable Ollama Models:")
    for idx, tag_obj in enumerate(tags, start=1):
        name = tag_obj.get("name", "<unknown>")
        print(f"  {idx}. {name}")

    while True:
        try:
            choice = int(input(f"\nEnter the number of the Ollama model you want to use (1–{len(tags)}): "))
            if 1 <= choice <= len(tags):
                selected = tags[choice - 1]
                OLLAMA_MODEL = selected.get("name", "")
                print(f"[INFO] Selected Ollama model: {OLLAMA_MODEL}\n")
                break
            else:
                print(f"[WARN] Please enter a number between 1 and {len(tags)}.")
        except ValueError:
            print("[WARN] Invalid input. Enter the numeric index of the model.")


# ————— SELECT TTS VOICE —————

def select_tts_voice():
    """
    Prompts the user to choose one female TTS voice from a variety of accents/languages.
    Sets the global TTS_VOICE accordingly.
    """
    global TTS_VOICE
    options = [
        ("American English (female)",      "en-US-JennyNeural"),
        ("British English (female)",       "en-GB-LibbyNeural"),
        ("Indian English (female)",        "en-IN-NeerjaNeural"),
        ("Australian English (female)",    "en-AU-NatashaNeural"),
        ("Irish English (female)",         "en-IE-EmilyNeural"),
        ("Canadian English (female)",      "en-CA-ClaraNeural"),
        ("Spanish (Spain, female)",        "es-ES-ElviraNeural"),
        ("Spanish (Mexico, female)",       "es-MX-DaliaNeural"),
        ("Spanish (Chile, female)",        "es-CL-MariaNeural"),
        ("Spanish (Colombia, female)",     "es-CO-SofiaNeural"),
        ("French (France, female)",        "fr-FR-DeniseNeural"),
        ("French (Canada, female)",        "fr-CA-SylvieNeural"),
        ("German (female)",                "de-DE-KatjaNeural"),
        ("German (Austria, female)",       "de-AT-IngridNeural"),
        ("Italian (female)",               "it-IT-ElsaNeural"),
        ("Portuguese (Portugal, female)",  "pt-PT-RaquelNeural"),
        ("Portuguese (Brazil, female)",    "pt-BR-FranciscaNeural"),
        ("Russian (female)",               "ru-RU-DariaNeural"),
        ("Arabic (MSA, female)",           "ar-EG-SalmaNeural"),
        ("Arabic (Saudi Arabia, female)",  "ar-SA-HananNeural"),
        ("Dutch (female)",                 "nl-NL-LotteNeural"),
        ("Swedish (female)",               "sv-SE-SofieNeural"),
        ("Danish (female)",                "da-DK-ChristelNeural"),
        ("Finnish (female)",               "fi-FI-SelmaNeural"),
        ("Polish (female)",                "pl-PL-MajaNeural"),
        ("Turkish (female)",               "tr-TR-EmelNeural"),
        ("Hindi (female)",                 "hi-IN-MadhurNeural"),
        ("Indonesian (female)",            "id-ID-GadisNeural"),
        ("Vietnamese (female)",            "vi-VN-HoaiMyNeural"),
        ("Thai (female)",                  "th-TH-PremwadeeNeural"),
        ("Greek (female)",                 "el-GR-NikiNeural"),
        ("Hungarian (female)",             "hu-HU-NoemiNeural"),
        ("Czech (female)",                 "cs-CZ-MiaNeural"),
        ("Romanian (female)",              "ro-RO-AlinaNeural"),
        ("Hebrew (female)",                "he-IL-BrigitteNeural"),
        ("Japanese (female)",              "ja-JP-NanamiNeural"),
        ("Korean (female)",                "ko-KR-SunHiNeural"),
        ("Chinese Mandarin (female)",      "zh-CN-XiaoxiaoNeural")
    ]

    print("\nAvailable TTS Voices (all female):")
    for idx, (label, code) in enumerate(options, start=1):
        print(f"  {idx}. {label}  (voice='{code}')")

    while True:
        try:
            choice = int(input(f"\nEnter the number of the TTS voice you want (1–{len(options)}): "))
            if 1 <= choice <= len(options):
                TTS_VOICE = options[choice - 1][1]
                print(f"[INFO] Selected TTS voice: {options[choice - 1][0]} (voice='{TTS_VOICE}')\n")
                break
            else:
                print(f"[WARN] Please enter a number between 1 and {len(options)}.")
        except ValueError:
            print("[WARN] Invalid input. Enter the numeric index of the voice.")


# ————— INITIALIZE WHISPER —————

def initialize_models():
    """
    Loads the Whisper model into memory. No local TTS engine needed.
    """
    global whisper_model
    print("[INFO] Loading Whisper model (base)…")
    whisper_model = WhisperModel("base", device="cpu")
    print("[INFO] Whisper model loaded.")


# ————— LISTEN FOR ONE UTTERANCE (VAD + AMPLITUDE) —————

def listen_and_transcribe():
    """
    Listens on the default recording device. Uses amplitude threshold + webrtcvad
    to detect a full utterance. Returns the transcript string (or empty if none).

    • Waits at least MIN_UTTERANCE_FRAMES of speech before allowing an end.
    • Requires SILENCE_THRESHOLD_FRAMES of continuous silence to cut off.
    • Grabs EXTRA_FRAMES (~210 ms) of audio after VAD signals “end” to avoid trailing cutoffs.
    """
    buffer_frames  = []
    triggered      = False
    num_silent     = 0
    num_buffered   = 0  # how many frames we’ve buffered so far

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=FRAME_SIZE,
        dtype="int16",
        channels=1,
        callback=None
    ) as stream:
        print("[INFO] Waiting for speech…")
        while True:
            # If TTS is speaking, skip capturing frames entirely
            if tts_playing.is_set():
                time.sleep(0.01)
                continue

            try:
                data, _ = stream.read(FRAME_SIZE)
            except Exception as e:
                print(f"[ERROR] Audio read error: {e}")
                continue

            if len(data) < FRAME_SIZE * 2:
                # Incomplete frame: skip
                continue

            # Convert raw bytes to int16 numpy array for amplitude check
            pcm     = np.frombuffer(data, dtype=np.int16)
            max_amp = np.abs(pcm).max()

            # If amplitude is below threshold, treat as silence
            if max_amp < AMPLITUDE_THRESHOLD:
                is_speech = False
            else:
                # Only if amplitude passes threshold do we run VAD
                is_speech = vad.is_speech(data, SAMPLE_RATE)

            if not triggered:
                # We haven’t detected speech yet
                if is_speech:
                    triggered    = True
                    buffer_frames.append(data)
                    num_buffered = 1
                    num_silent   = 0
                    print("[VAD] Speech detected, buffering…")
            else:
                # Already inside an utterance
                buffer_frames.append(data)
                num_buffered += 1

                if is_speech:
                    num_silent = 0
                else:
                    num_silent += 1

                    # Only end if we've buffered enough speech and seen enough silence
                    if (
                        num_buffered >= MIN_UTTERANCE_FRAMES
                        and num_silent > SILENCE_THRESHOLD_FRAMES
                    ):
                        print("[VAD] Detected sufficient silence after speech; grabbing extra frames…")
                        # Grab EXTRA_FRAMES unconditionally to catch trailing words
                        for _ in range(EXTRA_FRAMES):
                            try:
                                extra_data, _ = stream.read(FRAME_SIZE)
                                if len(extra_data) == FRAME_SIZE * 2:
                                    buffer_frames.append(extra_data)
                            except Exception:
                                break
                        break

        # Combine all buffered 16-bit PCM frames into one byte string
        pcm_data = b"".join(buffer_frames)
        buffer_frames.clear()
        triggered    = False
        num_silent    = 0
        num_buffered  = 0

        # Convert to float32 for Whisper
        audio_np = (np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0)

        # Write to a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            sf.write(tmp_wav.name, audio_np, SAMPLE_RATE)
            wav_path = tmp_wav.name

        # Transcribe with Whisper
        print("[WT] Running Whisper on captured utterance…")
        segments, _ = whisper_model.transcribe(wav_path, beam_size=5)
        os.remove(wav_path)

        transcript = "".join(seg.text for seg in segments).strip()
        return transcript


# ————— CALL OLLAMA —————

def query_ollama(user_text: str) -> str:
    """
    Sends the user_text + SYSTEM_INSTRUCTION to Ollama’s /v1/chat/completions endpoint.
    Returns the assistant’s reply (or an apology if it fails).
    """
    print(f"[LLM] Sending to Ollama: {user_text!r}")
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user",   "content": user_text}
        ]
    }
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        data  = resp.json()
        reply = data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[ERROR] Ollama API failed: {e}")
        reply = "Sorry, I encountered an error."
    print(f"[LLM] ← {reply!r}")
    return reply


# ————— ASYNC HELPER FOR EDGE-TTS —————

async def _edge_tts_generate(text: str, voice: str, output_path: str):
    """
    Uses edge_tts to generate an MP3 at `output_path` with the given `voice`.
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


# ————— TTS PLAYBACK (EDGE-TTS) —————

def speak_text(text: str):
    """
    Uses Edge-TTS to synthesize `text` in the selected voice,
    saves to a temporary MP3, plays it via playsound, then deletes it.
    While generating/playing, sets tts_playing so VAD is muted.
    """
    global TTS_VOICE
    if not TTS_VOICE:
        # Fallback to a default if not set
        TTS_VOICE = "en-US-JennyNeural"

    print(f"[TTS] Generating speech for: {text!r}  (voice={TTS_VOICE})")
    tts_playing.set()

    # Create a temp MP3 file
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # 1) Run the TTS generation asynchronously
        asyncio.run(_edge_tts_generate(text, TTS_VOICE, tmp_path))

        # 2) Play it back (blocking)
        print("[TTS] Playing generated audio…")
        playsound(tmp_path)

    except Exception as e:
        print(f"[TTS][ERROR] {e}")

    finally:
        # 3) Clean up
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        tts_playing.clear()
        print("[TTS] Done speaking.")


# ————— MAIN LOOP —————

def main_loop():
    """
    1) Listen → VAD + amplitude detect full utterance  
    2) Transcribe via Whisper  
    3) Query Ollama  
    4) Speak Ollama reply via Edge-TTS  
    5) Repeat
    """
    print("[INFO] Entering conversation loop. Speak when you hear silence…")
    while True:
        transcript = listen_and_transcribe()
        if not transcript:
            continue

        print(f"[WT] → Transcript: {transcript!r}")

        reply = query_ollama(transcript)
        speak_text(reply)


if __name__ == "__main__":
    # 1) Prompt for Ollama model selection
    select_ollama_model()

    # 2) Prompt for TTS voice selection (expanded global female voices)
    select_tts_voice()

    # 3) Initialize Whisper model
    initialize_models()

    # 4) Enter main conversation loop
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n[INFO] Exiting on user request.")
        os._exit(0)
