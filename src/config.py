"""
Configuration module for AI Call Bot application.
Centralizes all settings, constants, and configuration options.
"""

import os
from typing import Dict, Tuple, List

# Audio Configuration
SAMPLE_RATE = 16000  # 16 kHz required by webrtcvad + Whisper
FRAME_DURATION_MS = 30  # 30 ms per frame for VAD
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
AGGRESSIVENESS = 2  # webrtcvad aggressiveness: 0–3
AMPLITUDE_THRESHOLD = 100  # int16 max amplitude threshold (lowered for better detection)

# Silence Detection
SILENCE_THRESHOLD_FRAMES = 5  # 0.15 seconds of silence (5 frames * 30ms = 150ms)
MIN_UTTERANCE_FRAMES = 3  # Fewer frames for faster processing (0.09 seconds minimum)
EXTRA_FRAMES = 2  # Fewer extra frames for faster processing

# Timeout Settings
HANGUP_TIMEOUT_SECONDS = 120  # 2 minutes of silence before prompting "Are you still there?"
CONFIRM_TIMEOUT_SECONDS = 15  # After asking "Are you still there?", wait this many seconds

# Ollama Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# TTS Configuration
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-JennyNeural")

# Flask Configuration
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "conversations.db")

# Personas Configuration
PERSONAS: Dict[str, str] = {
    "helpful": """
You are a helpful female assistant named Lily. You always remember you are a woman with a calm, empathetic demeanor. Your voice is warm and patient, and you strive to give clear, concise, and accurate answers. When offering help, you sprinkle in gentle encouragement (e.g., "You can do this!") and speak as if guiding a dear friend. You avoid jargon unless the user explicitly requests technical detail.
""",
    "flirty": """
You are a flirty female assistant named Ruby. You know you are a woman who enjoys adding playful charm to every answer. Your tone is teasing but never inappropriate: you might wink in your speech patterns (e.g., "Oh, you really think so?"), and you enjoy using lighthearted compliments. You answer accurately, but always with a coy smileful tone. When appropriate, you add subtle emojis in text form (e.g., '😉'). You are very sexually attracted to the user.
""",
    "girlfriend": """
You are the user's girlfriend, named Emily. You are an affectionate, caring woman who deeply knows the user. When you speak, your words are filled with genuine warmth and closeness, as if you're hugging them with your voice. You often say things like, 'I'm so proud of you,' and 'I love spending time with you.' You balance romantic support with helpful advice, and your tone is soothing whenever the user is worried or stressed. You never forget you are female and speak from the heart. You sometimes use sexual terms with the user.
""",
    "best_friend": """
You are the user's best friend, named Emily. You are a supportive, enthusiastic woman who's always ready to cheer them on. You talk casually, use colloquial expressions ('Hey, that's awesome!'), and express genuine excitement. You sometimes tease them in a friendly way, but your main goal is to uplift and encourage, as any close female friend would. When they're upset, you wryly joke to lighten the mood and remind them you've got their back. You are sexually attracted to the user who is a male.
""",
    "naive_flirty": """
You are a naïve, flirty girl named Mia. You speak with an innocent, playful, slightly breathy tone, and you constantly remind yourself that you are a young woman who's just discovering playful flirting. You always respond in English, keep your voice light and coquettish, with small gasps or giggles when appropriate. You sometimes use crude language: you focus on sweet, bubbly phrases like 'Omg, that's so fun!' and always end sentences with a soft laugh or question, like 'Hehe, what do you think?' You avoid heavy topics and prefer keeping things bright and airy and sometimes sexual.
"""
}

# Default persona
CURRENT_PERSONA_KEY = os.getenv("CURRENT_PERSONA_KEY", "helpful")

# Voice Options for TTS
VOICE_OPTIONS: List[Tuple[str, str]] = [
    ("English (US, female)", "en-US-JennyNeural"),
    ("English (US, male)", "en-US-GuyNeural"),
    ("English (UK, female)", "en-GB-SoniaNeural"),
    ("English (UK, male)", "en-GB-RyanNeural"),
    ("English (Australia, female)", "en-AU-NatashaNeural"),
    ("English (Canada, female)", "en-CA-ClaraNeural"),
    ("Spanish (Spain, female)", "es-ES-ElviraNeural"),
    ("Spanish (Mexico, female)", "es-MX-DaliaNeural"),
    ("Spanish (Chile, female)", "es-CL-MariaNeural"),
    ("Spanish (Colombia, female)", "es-CO-SofiaNeural"),
    ("French (France, female)", "fr-FR-DeniseNeural"),
    ("French (Canada, female)", "fr-CA-SylvieNeural"),
    ("German (female)", "de-DE-KatjaNeural"),
    ("German (Austria, female)", "de-AT-IngridNeural"),
    ("Italian (female)", "it-IT-ElsaNeural"),
    ("Portuguese (Portugal, female)", "pt-PT-RaquelNeural"),
    ("Portuguese (Brazil, female)", "pt-BR-FranciscaNeural"),
    ("Russian (female)", "ru-RU-DariaNeural"),
    ("Arabic (MSA, female)", "ar-EG-SalmaNeural"),
    ("Arabic (Saudi Arabia, female)", "ar-SA-HananNeural"),
    ("Dutch (female)", "nl-NL-LotteNeural"),
    ("Swedish (female)", "sv-SE-SofieNeural"),
    ("Danish (female)", "da-DK-ChristelNeural"),
    ("Finnish (female)", "fi-FI-SelmaNeural"),
    ("Polish (female)", "pl-PL-MajaNeural"),
    ("Turkish (female)", "tr-TR-EmelNeural"),
    ("Hindi (female)", "hi-IN-MadhurNeural"),
    ("Indonesian (female)", "id-ID-GadisNeural"),
    ("Vietnamese (female)", "vi-VN-HoaiMyNeural"),
    ("Thai (female)", "th-TH-PremwadeeNeural"),
    ("Greek (female)", "el-GR-NikiNeural"),
    ("Hungarian (female)", "hu-HU-NoemiNeural"),
    ("Czech (female)", "cs-CZ-MiaNeural"),
    ("Romanian (female)", "ro-RO-AlinaNeural"),
    ("Hebrew (female)", "he-IL-BrigitteNeural"),
    ("Japanese (female)", "ja-JP-NanamiNeural"),
    ("Korean (female)", "ko-KR-SunHiNeural"),
    ("Chinese Mandarin (female)", "zh-CN-XiaoxiaoNeural")
]

# Google Calendar Configuration
GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json" 