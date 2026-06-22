"""
transcriber.py — download Twilio call recordings and transcribe with Whisper.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
import openai
from twilio.rest import Client as TwilioClient

import config

logger = logging.getLogger(__name__)

_openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
_twilio_client = TwilioClient(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)


# ── Recording download ─────────────────────────────────────────────────────────

def wait_for_recording(call_sid: str, max_wait: int = 120, poll_interval: int = 5) -> str | None:
    """
    Poll Twilio until the recording for *call_sid* is available, then return the
    recording SID.  Returns None if no recording appears within *max_wait* seconds.
    """
    logger.info("[%s] Waiting for Twilio recording…", call_sid)
    deadline = time.time() + max_wait
    while time.time() < deadline:
        recordings = _twilio_client.recordings.list(call_sid=call_sid, limit=1)
        if recordings:
            rec = recordings[0]
            if rec.status in ("completed", "no-audio"):
                logger.info("[%s] Recording ready: %s (status=%s)", call_sid, rec.sid, rec.status)
                return rec.sid
        time.sleep(poll_interval)
    logger.warning("[%s] Timed out waiting for recording.", call_sid)
    return None


def download_recording(recording_sid: str, call_sid: str) -> str:
    """
    Download a Twilio recording (dual-channel MP3) to calls/audio/.
    Returns the local file path.
    """
    os.makedirs(config.AUDIO_DIR, exist_ok=True)
    output_path = os.path.join(config.AUDIO_DIR, f"{call_sid}_recording.mp3")

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}"
        f"/Recordings/{recording_sid}.mp3"
    )
    response = requests.get(
        url,
        auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN),
        timeout=60,
    )
    response.raise_for_status()

    Path(output_path).write_bytes(response.content)
    logger.info("[%s] Recording saved → %s (%d bytes)", call_sid, output_path, len(response.content))
    return output_path


# ── Transcription ──────────────────────────────────────────────────────────────

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe an audio file with OpenAI Whisper.
    Returns the full transcript text.
    """
    logger.info("Transcribing: %s", audio_path)
    with open(audio_path, "rb") as audio_file:
        result = _openai_client.audio.transcriptions.create(
            model=config.OPENAI_WHISPER_MODEL,
            file=audio_file,
            response_format="text",
        )
    transcript: str = result if isinstance(result, str) else result.text  # type: ignore[union-attr]
    logger.info("Transcript (%d chars): %s…", len(transcript), transcript[:80])
    return transcript


def save_transcript(call_sid: str, transcript_text: str, metadata: dict[str, Any] | None = None) -> str:
    """
    Save a transcript to calls/transcripts/<call_sid>.json.
    Returns the saved file path.
    """
    os.makedirs(config.TRANSCRIPT_DIR, exist_ok=True)
    output_path = os.path.join(config.TRANSCRIPT_DIR, f"{call_sid}.json")

    data: dict[str, Any] = {
        "call_sid": call_sid,
        "transcript": transcript_text,
    }
    if metadata:
        data.update(metadata)

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    logger.info("[%s] Transcript saved → %s", call_sid, output_path)
    return output_path


def process_call(call_sid: str) -> dict[str, str]:
    """
    High-level helper: wait for the recording, download it, transcribe it,
    and persist the transcript.

    Returns a dict with keys ``recording_path`` and ``transcript_path``.
    """
    recording_sid = wait_for_recording(call_sid)
    if not recording_sid:
        logger.error("[%s] No recording found — skipping transcription.", call_sid)
        return {}

    recording_path = download_recording(recording_sid, call_sid)
    transcript_text = transcribe_audio(recording_path)
    transcript_path = save_transcript(call_sid, transcript_text, {"recording_path": recording_path})

    return {
        "recording_path": recording_path,
        "transcript_path": transcript_path,
        "transcript": transcript_text,
    }
