"""
tts.py — convert text to speech and return a WAV/MP3 bytes buffer.

Uses the OpenAI Audio Speech API (tts-1 or tts-1-hd).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import openai

import config

logger = logging.getLogger(__name__)

_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)


def text_to_speech(text: str, output_path: str | None = None) -> bytes:
    """
    Convert *text* to speech audio (MP3).

    Parameters
    ----------
    text:
        The words to speak.
    output_path:
        If provided, write the MP3 file to this path in addition to returning bytes.

    Returns
    -------
    bytes
        Raw MP3 audio data.
    """
    logger.debug("TTS: %r (voice=%s)", text[:60], config.OPENAI_TTS_VOICE)

    response = _client.audio.speech.create(
        model=config.OPENAI_TTS_MODEL,
        voice=config.OPENAI_TTS_VOICE,   # type: ignore[arg-type]
        input=text,
        response_format="mp3",
    )
    audio_bytes: bytes = response.read()

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(audio_bytes)
        logger.info("TTS audio saved → %s", output_path)

    return audio_bytes


def save_tts_for_twilio(text: str, call_sid: str, turn: int) -> str:
    """
    Generate TTS for a call turn and save to the audio directory.

    Returns the local file path (relative to the project root).
    """
    filename = f"{call_sid}_turn_{turn:03d}_patient.mp3"
    output_path = os.path.join(config.AUDIO_DIR, filename)
    # text_to_speech creates parent directories via Path.mkdir
    text_to_speech(text, output_path=output_path)
    return output_path
