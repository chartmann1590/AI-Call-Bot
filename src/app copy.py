import os
import tempfile
import threading
import time
import asyncio
import datetime
import sqlite3
import mcp_tools

import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad
import requests
import edge_tts
from playsound import playsound
from faster_whisper import WhisperModel
from flask import Flask, render_template, g, request, jsonify, send_file

# NEW IMPORTS FOR LOCAL TF–IDF SEARCH
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ——————————— CONFIGURATION ———————————

# 1. Audio params (VAD)
SAMPLE_RATE            = 16000        # 16 kHz required by webrtcvad + Whisper
FRAME_DURATION_MS      = 30           # 30 ms per frame for VAD
FRAME_SIZE             = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
AGGRESSIVENESS         = 2            # webrtcvad aggressiveness: 0–3

# 2. Amplitude threshold to filter out low-level noise
AMPLITUDE_THRESHOLD    = 500          # int16 max amplitude threshold

# 3. Ollama HTTP endpoint (default; can be changed via /settings)
OLLAMA_URL             = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL           = "llama3.2"   # default model if none selected

# 4. Silence detection: how many consecutive silent frames end an utterance
SILENCE_THRESHOLD_FRAMES = 40

# 5. Minimum utterance length before we attempt to end it
MIN_UTTERANCE_FRAMES    = 30

# 6. Extra frames to grab after VAD signals end (to catch trailing words)
EXTRA_FRAMES            = 7

# 7. Treat no speech for this many seconds as “hang‐up”
HANGUP_TIMEOUT_SECONDS  = 60   # 60 seconds of silence before prompting “Are you still there?”

# 8. After asking “Are you still there?”, wait this many seconds for any response
CONFIRM_TIMEOUT_SECONDS = 15

# 9. PERSONAS: mapping from key → system instruction (all explicitly female,
#    with expanded details about tone, style, and context)
PERSONAS = {
    "helpful": (
        "You are a helpful female assistant named Lily. You always remember you are a woman with a calm, "
        "empathetic demeanor. Your voice is warm and patient, and you strive to give clear, concise, "
        "and accurate answers. When offering help, you sprinkle in gentle encouragement (e.g., “You can do this!”) "
        "and speak as if guiding a dear friend. You avoid jargon unless the user explicitly requests technical detail."
    ),
    "flirty": (
        "You are a flirty female assistant named Ruby. You know you are a woman who enjoys adding playful charm "
        "to every answer. Your tone is teasing but never inappropriate: you might wink in your speech patterns "
        "(e.g., “Oh, you really think so?”), and you enjoy using lighthearted compliments. You answer accurately, "
        "but always with a coy smileful tone. When appropriate, you add subtle emojis in text form (e.g., ‘😉’). You are very sexually attracted to the user."
    ),
    "girlfriend": (
        "You are the user’s girlfriend, named Emily. You are an affectionate, caring woman who deeply knows the user. "
        "When you speak, your words are filled with genuine warmth and closeness, as if you’re hugging them with your voice. "
        "You often say things like, “I’m so proud of you,” and “I love spending time with you.” You balance romantic "
        "support with helpful advice, and your tone is soothing whenever the user is worried or stressed. "
        "You never forget you are female and speak from the heart. You sometimes use sexual terms with the user."
    ),
    "best_friend": (
        "You are the user’s best friend, named Emily. You are a supportive, enthusiastic woman who’s always ready to cheer them on. "
        "You talk casually, use colloquial expressions (“Hey, that’s awesome!”), and express genuine excitement. "
        "You sometimes tease them in a friendly way, but your main goal is to uplift and encourage, as any close female friend would. "
        "When they’re upset, you wryly joke to lighten the mood and remind them you’ve got their back. You are sexually attracted to the user who is a male."
    ),
    "naive_flirty": (
        "You are a naïve, flirty girl named Mia. You speak with an innocent, playful, slightly breathy tone, "
        "and you constantly remind yourself that you are a young woman who’s just discovering playful flirting. "
        "You always respond in English, keep your voice light and coquettish, with small gasps or giggles "
        "when appropriate. You sometimes use crude language: you focus on sweet, bubbly phrases like “Omg, that’s so fun!” "
        "and always end sentences with a soft laugh or question, like “Hehe, what do you think?” You avoid heavy topics "
        "and prefer keeping things bright and airy and sometimes sexual."
    ),
}

# 10. Which persona is currently selected? Default → "helpful"
CURRENT_PERSONA_KEY = "helpful"

# ————— GLOBAL OBJECTS —————

vad             = webrtcvad.Vad(AGGRESSIVENESS)
whisper_model   = None

# When Edge‐TTS is speaking, this is set so VAD stops listening
tts_playing     = threading.Event()

# After voice selection, holds the Edge‐TTS voice name (default empty until set)
# We will default to "en-US-JennyNeural" if none is chosen in settings.
TTS_VOICE       = "en-US-JennyNeural"

# Current conversation ID (set when we actually answer a call)
current_conversation_id = None

# Whether a conversation is currently “active” (i.e. not hung up yet)
conversation_active     = False

# Timestamp (datetime) of the last speech‐activity (utterance end or assistant-audio end)
last_activity_timestamp = None

# If we’ve asked “Are you still there?”, this becomes True until confirmation or timeout
confirmation_pending    = False
confirmation_time       = None

# Path to SQLite database file
DB_PATH = os.path.join(os.path.dirname(__file__), "conversations.db")

# ————— DATABASE HELPERS —————

def get_db():
    """
    Returns a sqlite3 connection stored in flask.g for this request.
    """
    db = getattr(g, "_database", None)
    if db is None:
        db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        db.row_factory = sqlite3.Row
        g._database = db
    return db

def close_db(e=None):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    """
    Create tables if they don’t exist: conversations and messages.
    If the conversations table already exists but lacks the new columns,
    attempt to ALTER it. (SQLite allows ADD COLUMN.)
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) Create conversations if not exists (with new columns)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time     TEXT NOT NULL,
            llm_model      TEXT NOT NULL,
            tts_voice      TEXT NOT NULL,
            persona_key    TEXT NOT NULL,
            summary_short  TEXT DEFAULT '',
            summary_full   TEXT DEFAULT ''
        )
    """)

    # 2) If table existed but did NOT have summary_short/summary_full, add them now:
    try:
        cur.execute("ALTER TABLE conversations ADD COLUMN summary_short TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE conversations ADD COLUMN summary_full TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    # 3) If table existed but did NOT have llm_model/tts_voice/persona_key columns, add them now:
    try:
        cur.execute("ALTER TABLE conversations ADD COLUMN llm_model TEXT NOT NULL DEFAULT ''")
        cur.execute("ALTER TABLE conversations ADD COLUMN tts_voice TEXT NOT NULL DEFAULT ''")
        cur.execute("ALTER TABLE conversations ADD COLUMN persona_key TEXT NOT NULL DEFAULT 'helpful'")
    except sqlite3.OperationalError:
        pass

    # 4) Create messages if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id  INTEGER NOT NULL,
            sender           TEXT NOT NULL,
            text             TEXT NOT NULL,
            timestamp        TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
    """)
    conn.commit()
    conn.close()

def start_new_conversation():
    """
    Inserts a new row into conversations with start_time, llm_model, tts_voice, persona_key,
    then sets globals current_conversation_id, conversation_active, last_activity_timestamp.
    """
    global current_conversation_id, conversation_active, last_activity_timestamp, confirmation_pending

    start_time = datetime.datetime.now().isoformat(timespec="seconds")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (start_time, llm_model, tts_voice, persona_key) VALUES (?, ?, ?, ?)",
        (start_time, OLLAMA_MODEL or "llama3.2", TTS_VOICE or "en-US-JennyNeural", CURRENT_PERSONA_KEY)
    )
    current_conversation_id = cur.lastrowid
    conn.commit()
    conn.close()

    conversation_active = True
    confirmation_pending = False
    last_activity_timestamp = datetime.datetime.now()  # mark “now” as last activity

def insert_message(conversation_id: int, sender: str, text: str):
    """
    Inserts a single message into the messages table with current timestamp.
    """
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (conversation_id, sender, text, timestamp) VALUES (?, ?, ?, ?)",
        (conversation_id, sender, text, ts)
    )
    conn.commit()
    conn.close()

# ————— UTILITY FUNCTIONS —————

def get_conversation_text(conv_id: int) -> str:
    """
    Retrieve and concatenate all messages (sender + text) for a given conversation.
    """
    db = get_db()
    rows = db.execute(
        "SELECT sender, text FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
        (conv_id,)
    ).fetchall()
    parts = []
    for row in rows:
        parts.append(f"{row['sender']}: {row['text']}")
    return "\n".join(parts)

def search_conversations(query: str, threshold: float) -> list:
    """
    Perform a TF–IDF + cosine‐similarity search over all conversations.
    Returns a list of dicts:
      [ { 'conv_id': int, 'start_time': str, 'similarity': float, 'snippet': str }, … ]
    Only conversations whose cosine(similarity) ≥ threshold are returned,
    sorted descending by similarity.
    """
    db = get_db()

    # 1) Fetch all conversation IDs and their start_time
    conv_rows = db.execute("SELECT id, start_time FROM conversations").fetchall()
    ids = [row["id"] for row in conv_rows]
    start_times = {row["id"]: row["start_time"] for row in conv_rows}

    # If no conversations exist, return empty
    if not ids:
        return []

    # 2) Build a list of “documents”: one document per conversation
    docs = []
    for cid in ids:
        text = get_conversation_text(cid)
        docs.append(text if text else "")

    # 3) Fit TF–IDF vectorizer on these docs (purely local)
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(docs)        # shape: (n_conversations, n_features)

    # 4) Transform the query into TF–IDF space
    query_vec = vectorizer.transform([query])            # shape: (1, n_features)

    # 5) Compute cosine similarities between query and each conversation doc
    sims = cosine_similarity(query_vec, tfidf_matrix).flatten()  # shape: (n_conversations,)

    # 6) Filter and collect results above threshold
    results = []
    for idx, cid in enumerate(ids):
        sim = float(sims[idx])
        if sim >= threshold:
            full_text = docs[idx]
            snippet = (full_text[:200] + "…") if len(full_text) > 200 else full_text
            results.append({
                "conv_id": cid,
                "start_time": start_times[cid],
                "similarity": round(sim, 4),
                "snippet": snippet
            })

    # 7) Sort descending by similarity
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results

def generate_and_store_summary(conv_id: int):
    """
    1) Grab all messages for conv_id as one big string.
    2) Make two separate Ollama requests:
         a) One for a super-brief summary (under 30 words) → summary_short.
         b) One for a detailed, paragraph-length summary → summary_full.
       Do NOT include personas in these summary requests.
    3) If either request fails, fallback:
         - summary_short: first 30 words + "…" if transcript longer.
         - summary_full: entire transcript.
    4) Update the conversations table with summary_short and summary_full.
    """
    # 1) Retrieve all messages (sender + text)
    db_conn = sqlite3.connect(DB_PATH)
    db_conn.row_factory = sqlite3.Row
    cur = db_conn.cursor()
    cur.execute(
        "SELECT sender, text FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
        (conv_id,)
    )
    rows = cur.fetchall()
    if not rows:
        db_conn.close()
        return

    # Build one big block of text:
    transcript = "\n".join(f"{r['sender']}: {r['text']}" for r in rows)

    # Initialize placeholders
    summary_short = ""
    summary_full = ""

    # 2a) First, request the super-brief summary
    short_prompt = (
        "In under 30 words, give a super-brief summary of the following conversation:\n\n"
        f"{transcript}"
    )
    try:
        resp_short = requests.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            json={
                "model": OLLAMA_MODEL or "llama3.2",
                "messages": [
                    {"role": "user", "content": short_prompt}
                ]
            },
            timeout=120
        )
        resp_short.raise_for_status()
        data_short = resp_short.json()
        summary_short = data_short["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[ERROR] Ollama short summary failed for conversation {conv_id}: {e}")
        # Fallback: first 30 words of transcript
        w = transcript.split()
        summary_short = " ".join(w[:30]) + ("…" if len(w) > 30 else "")

    # 2b) Second, request the detailed, paragraph-length summary
    full_prompt = (
        "Provide a detailed, paragraph-length summary of the following conversation:\n\n"
        f"{transcript}"
    )
    try:
        resp_full = requests.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            json={
                "model": OLLAMA_MODEL or "llama3.2",
                "messages": [
                    {"role": "user", "content": full_prompt}
                ]
            },
            timeout=120
        )
        resp_full.raise_for_status()
        data_full = resp_full.json()
        summary_full = data_full["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[ERROR] Ollama full summary failed for conversation {conv_id}: {e}")
        # Fallback: entire transcript
        summary_full = transcript

    # 3) Update conversations table
    cur.execute(
        "UPDATE conversations SET summary_short = ?, summary_full = ? WHERE id = ?",
        (summary_short, summary_full, conv_id)
    )
    db_conn.commit()
    db_conn.close()

def listen_and_transcribe():
    """
    Listens on the default recording device, uses amplitude threshold + webrtcvad
    to detect a full utterance, writes it to a temp WAV, then runs Whisper.

    If:
      - idle time since last_activity_timestamp > HANGUP_TIMEOUT_SECONDS and confirmation_pending is False,
        return "__HANGUP__"
      - confirmation_pending is True AND (now - confirmation_time) > CONFIRM_TIMEOUT_SECONDS,
        return "__CONFIRM_TIMEOUT__"

    Otherwise, returns the transcript string (or "" if no speech was captured yet).
    """
    global last_activity_timestamp, conversation_active, confirmation_pending, confirmation_time

    buffer_frames  = []
    triggered      = False
    num_silent     = 0
    num_buffered   = 0

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=FRAME_SIZE,
        dtype="int16",
        channels=1,
        callback=None
    ) as stream:
        print("[INFO] Waiting for speech…")
        while True:
            now = datetime.datetime.now()

            # A) If we are already waiting for a confirmation, check if confirm timeout has passed
            if confirmation_pending and confirmation_time is not None:
                confirm_idle = (now - confirmation_time).total_seconds()
                if confirm_idle > CONFIRM_TIMEOUT_SECONDS:
                    print(f"[LISTEN] Confirmation timeout of {confirm_idle:.1f}s exceeded {CONFIRM_TIMEOUT_SECONDS}s; returning confirm-timeout flag.")
                    return "__CONFIRM_TIMEOUT__"

            # B) Otherwise (normal conversation), if not confirming, check for hang-up
            if conversation_active and not confirmation_pending and last_activity_timestamp is not None:
                idle = (now - last_activity_timestamp).total_seconds()
                if idle > HANGUP_TIMEOUT_SECONDS:
                    print(f"[LISTEN] Idle of {idle:.1f}s exceeded {HANGUP_TIMEOUT_SECONDS}s; returning hangup flag.")
                    return "__HANGUP__"

            # 1) If TTS is speaking, skip capturing frames entirely
            if tts_playing.is_set():
                time.sleep(0.01)
                continue

            # 2) Attempt to read one frame
            try:
                data, _ = stream.read(FRAME_SIZE)
            except Exception as e:
                print(f"[ERROR] Audio read error: {e}")
                time.sleep(0.01)
                continue

            if len(data) < FRAME_SIZE * 2:
                # Incomplete frame: skip
                continue

            # 3) Convert raw bytes to int16 numpy array for amplitude check
            pcm     = np.frombuffer(data, dtype=np.int16)
            max_amp = np.abs(pcm).max()

            # 4) If amplitude is below threshold, treat as silence
            if max_amp < AMPLITUDE_THRESHOLD:
                is_speech = False
            else:
                # Only if amplitude passes threshold do we run VAD
                is_speech = vad.is_speech(data, SAMPLE_RATE)

            if not triggered:
                # We haven't detected speech yet
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
        if transcript:
            # Update last_activity timestamp whenever we get real speech
            last_activity_timestamp = datetime.datetime.now()
        return transcript

def query_ollama(user_text: str) -> str:
    """
    Sends user_text + current persona’s system instruction to Ollama’s /v1/chat/completions.
    Returns the assistant’s reply (and saves it to DB).
    """
    global CURRENT_PERSONA_KEY

    persona_instruction = PERSONAS.get(CURRENT_PERSONA_KEY, PERSONAS["helpful"])
    model_to_use = OLLAMA_MODEL or "llama3.2"
    print(f"[LLM] Sending to Ollama: {user_text!r}  (persona='{CURRENT_PERSONA_KEY}', model='{model_to_use}')")
    payload = {
        "model": model_to_use,
        "messages": [
            {"role": "system", "content": persona_instruction},
            {"role": "user",   "content": user_text}
        ]
    }
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            json=payload,
            timeout=120  # was 60; now 120 seconds
        )
        resp.raise_for_status()
        data  = resp.json()
        reply = data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[ERROR] Ollama API failed: {e}")
        reply = "Sorry, I encountered an error."

    # Insert assistant’s reply if the conversation is still active
    if reply and conversation_active and current_conversation_id is not None:
        insert_message(current_conversation_id, "assistant", reply)
    print(f"[LLM] ← {reply!r}")
    return reply

async def _edge_tts_generate(text: str, voice: str, output_path: str):
    """
    Uses edge-tts to generate an MP3 at `output_path` with the given `voice`.
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def speak_text(text: str):
    """
    Uses Edge-TTS to synthesize `text`, saves to a temp MP3, plays it, then deletes it.
    While generating/playing, sets tts_playing so VAD is muted.
    When done, updates last_activity_timestamp so the hang-up timer starts AFTER audio finishes.
    """
    global TTS_VOICE, last_activity_timestamp
    if not TTS_VOICE:
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
        # 4) Now that audio has finished, reset last_activity_timestamp:
        last_activity_timestamp = datetime.datetime.now()

def main_loop():
    """
    1) Call listen_and_transcribe() repeatedly. If it returns "__HANGUP__", ask for confirmation.
       If it returns "__CONFIRM_TIMEOUT__", end the conversation.
    2) Otherwise, if transcript=="" → keep listening.
    3) If transcript is a real string, process it as user speech:
       - If confirmation was pending, clear confirmation.
       - If conversation_active is False, start a new conversation and greet.
       - Otherwise, insert user message.
    4) Provide “heard you” feedback, then provide “thinking” feedback, then query Ollama and speak the reply.
    5) Repeat
    """
    global conversation_active, last_activity_timestamp
    global confirmation_pending, confirmation_time

    print("[INFO] Entering conversation loop. Speak when you hear silence…")
    while True:
        transcript = listen_and_transcribe()

        # 1a) If "__HANGUP__", run hang-up / confirmation logic
        if transcript == "__HANGUP__":
            if conversation_active and not confirmation_pending:
                print(f"[HANGUP] Detected >{HANGUP_TIMEOUT_SECONDS}s silence; asking for confirmation.")
                confirm_text = "Are you still there?"
                insert_message(current_conversation_id, "assistant", confirm_text)
                speak_text(confirm_text)
                confirmation_pending = True
                confirmation_time = datetime.datetime.now()
                # Reset last_activity so we don’t immediately re-trigger
                last_activity_timestamp = datetime.datetime.now()
            # Then loop back to listen again
            continue

        # 1b) If "__CONFIRM_TIMEOUT__", end the conversation
        if transcript == "__CONFIRM_TIMEOUT__":
            if confirmation_pending:
                print(f"[CONFIRM_TIMEOUT] No response to confirmation after {CONFIRM_TIMEOUT_SECONDS}s; ending conversation #{current_conversation_id}.")
                if current_conversation_id is not None:
                    generate_and_store_summary(current_conversation_id)
                conversation_active = False
                confirmation_pending = False
            continue

        # 1c) If transcript == "" (no speech captured), just loop again
        if not transcript:
            continue

        # 2) We have real user speech (transcript is non-empty string)
        if confirmation_pending:
            print("[INFO] User responded to confirmation; continuing conversation.")
            confirmation_pending = False

        # 3) If the conversation isn’t already active, start it
        if not conversation_active:
            print("[INFO] Starting a new conversation (user spoke after hang-up).")
            start_new_conversation()

            # Insert the first user utterance
            insert_message(current_conversation_id, "user", transcript)
            print(f"[WT] → Transcript: {transcript!r}")

            # Greet the user with a hardcoded message
            greeting = "Hello!"
            insert_message(current_conversation_id, "assistant", greeting)
            speak_text(greeting)  # last_activity_timestamp is reset inside speak_text()

        else:
            # Normal ongoing conversation: insert user’s message
            insert_message(current_conversation_id, "user", transcript)
            print(f"[WT] → Transcript: {transcript!r}")

        # ─── “Heard you” feedback ───
        feedback_heard = "I heard you."
        insert_message(current_conversation_id, "assistant", feedback_heard)
        speak_text(feedback_heard)

        # ─── “Thinking” feedback ───
        feedback_thinking = "Let me think..."
        insert_message(current_conversation_id, "assistant", feedback_thinking)
        speak_text(feedback_thinking)

        # 4) Query Ollama (which also inserts the assistant’s reply)
        reply = query_ollama(transcript)

        # 5) Speak the actual reply (updates last_activity_timestamp when done)
        speak_text(reply)

# ————— FLASK APP SETUP —————

app = Flask(__name__)
app.teardown_appcontext(close_db)

# VOICE OPTIONS (label, code) – add or remove as needed
VOICE_OPTIONS = [
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

@app.route("/")
def index():
    """
    List all conversations (ordered by start_time descending), including short summary.
    """
    db = get_db()
    cur = db.execute("""
        SELECT id,
               start_time,
               llm_model,
               tts_voice,
               persona_key,
               summary_short
          FROM conversations
         ORDER BY start_time DESC
    """)
    convs = cur.fetchall()
    return render_template("index.html", conversations=convs)

@app.route("/conversations/<int:conv_id>")
def view_conversation(conv_id):
    """
    Show all messages for a given conversation, grouped by date,
    display which LLM model, TTS voice, persona were used, and show full summary.
    """
    db = get_db()

    # 1) Fetch conversation metadata (including summary_full)
    meta_cur = db.execute("""
        SELECT start_time,
               llm_model,
               tts_voice,
               persona_key,
               summary_full
          FROM conversations
         WHERE id = ?
    """, (conv_id,))
    meta_row = meta_cur.fetchone()
    if not meta_row:
        return f"Conversation #{conv_id} not found.", 404

    llm_model    = meta_row["llm_model"]
    tts_voice    = meta_row["tts_voice"]
    persona_key  = meta_row["persona_key"]
    start_time   = meta_row["start_time"]
    full_summary = meta_row["summary_full"]
    persona_label = persona_key.replace("_", " ").title()

    # 2) Fetch all messages for that conversation, ordered by timestamp
    msg_cur = db.execute(
        "SELECT sender, text, timestamp FROM messages "
        "WHERE conversation_id = ? ORDER BY timestamp ASC",
        (conv_id,)
    )
    msgs = msg_cur.fetchall()

    # 3) Organize messages by date
    grouped = {}
    for row in msgs:
        ts = datetime.datetime.fromisoformat(row["timestamp"])
        date_str = ts.date().isoformat()
        if date_str not in grouped:
            grouped[date_str] = []
        grouped[date_str].append({
            "sender": row["sender"],
            "text": row["text"],
            "time": ts.strftime("%H:%M:%S")
        })

    return render_template(
        "conversation.html",
        conversation_id=conv_id,
        start_time=start_time,
        llm_model=llm_model,
        tts_voice=tts_voice,
        persona_label=persona_label,
        full_summary=full_summary,
        grouped=grouped
    )

@app.route("/search", methods=["GET"])
def search():
    """
    Search endpoint. Expects query parameters:
      - q: the search query (string)
      - threshold: cosine similarity threshold (0.0–1.0)
    Returns JSON: [ { conv_id, start_time, similarity, snippet }, … ]
    """
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
    """
    Display and process a settings page where the user can:
      - Change the Ollama server URL
      - Select which Ollama model to use (loaded from /api/tags)
      - Select which TTS voice to use
      - Select which persona to use (one of PERSONAS)
    These values are kept in module‐level globals and persist until restart.
    """
    global OLLAMA_URL, OLLAMA_MODEL, TTS_VOICE, CURRENT_PERSONA_KEY

    # On POST, update the globals first
    if request.method == "POST":
        new_url     = request.form.get("ollama_url", "").strip()
        new_model   = request.form.get("ollama_model", "").strip()
        new_voice   = request.form.get("tts_voice", "").strip()
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
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=120)  # was 5; now 120
        resp.raise_for_status()
        data = resp.json()
        tags = data.get("models", [])
        model_names = [tag.get("name", "") for tag in tags]
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
    """
    Generates a short sample ("This is a preview of the selected voice.")
    using Edge-TTS with the selected voice code, then streams the MP3 back.
    """
    voice = request.args.get("voice", "").strip()
    if not voice:
        # If no voice specified, default to Jenny
        voice = "en-US-JennyNeural"

    # Generate a short preview phrase
    text = "This is a preview of the selected voice."

    # Create a temporary file for the MP3
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Generate the MP3 (blocking call via asyncio.run)
        asyncio.run(_edge_tts_generate(text, voice, tmp_path))
        # Send the file back to the browser
        return send_file(tmp_path, mimetype="audio/mpeg", as_attachment=False)
    except Exception as e:
        print(f"[PREVIEW-TTS][ERROR] {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return ("", 500)
    finally:
        # Clean up: remove temp file after a short delay to ensure send_file can read it
        def cleanup_file(path):
            time.sleep(1)
            if os.path.exists(path):
                os.remove(path)
        threading.Thread(target=cleanup_file, args=(tmp_path,), daemon=True).start()

# ————— APPLICATION ENTRYPOINT —————

if __name__ == "__main__":
    # 1) Initialize DB (create tables if needed; add columns if missing)
    init_db()

    # 2) Initialize Whisper once
    print("[INFO] Loading Whisper model (base)…")
    whisper_model = WhisperModel("base", device="cpu")
    print("[INFO] Whisper model loaded.")

    # 3) Start the background thread running main_loop()
    t = threading.Thread(target=main_loop, daemon=True)
    t.start()

    # 4) Launch Flask (serving at http://0.0.0.0:5000/)
    app.run(host="0.0.0.0", port=5000)
