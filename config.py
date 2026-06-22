"""
config.py — centralised configuration loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Twilio ────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID: str = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN: str = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_PHONE_NUMBER: str = os.environ["TWILIO_PHONE_NUMBER"]   # your Twilio number
TARGET_PHONE_NUMBER: str = os.getenv("TARGET_PHONE_NUMBER", "+18054398008")

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]
OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
OPENAI_TTS_MODEL: str = os.getenv("OPENAI_TTS_MODEL", "tts-1")
OPENAI_TTS_VOICE: str = os.getenv("OPENAI_TTS_VOICE", "nova")          # warm female voice
OPENAI_WHISPER_MODEL: str = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")

# ── Webhook / tunnel ──────────────────────────────────────────────────────────
# Public URL exposed by ngrok (or any reverse-proxy) pointing at app.py
WEBHOOK_BASE_URL: str = os.environ["WEBHOOK_BASE_URL"]   # e.g. https://abc123.ngrok.io
WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "5000"))

# ── Call settings ─────────────────────────────────────────────────────────────
NUM_CALLS: int = int(os.getenv("NUM_CALLS", "10"))
RECORDING_CHANNELS: str = os.getenv("RECORDING_CHANNELS", "dual")   # dual = both legs

# ── Local paths ───────────────────────────────────────────────────────────────
CALLS_DIR: str = os.getenv("CALLS_DIR", "calls")
AUDIO_DIR: str = os.path.join(CALLS_DIR, "audio")
TRANSCRIPT_DIR: str = os.path.join(CALLS_DIR, "transcripts")
BUG_REPORT_PATH: str = os.getenv("BUG_REPORT_PATH", "BUGS.md")

# ── Patient persona ───────────────────────────────────────────────────────────
PATIENT_NAME: str = os.getenv("PATIENT_NAME", "Sarah Johnson")
PATIENT_DOB: str = os.getenv("PATIENT_DOB", "March 14, 1985")
PATIENT_INSURANCE: str = os.getenv("PATIENT_INSURANCE", "BlueCross BlueShield PPO")
PATIENT_REASON: str = os.getenv(
    "PATIENT_REASON",
    "I need to schedule a follow-up appointment for my lower back pain"
)
