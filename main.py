"""
main.py — orchestrates running NUM_CALLS outbound calls to the target number.

Usage:
    python main.py

Prerequisites:
    1. Copy .env.example → .env and fill in all values.
    2. Start a public tunnel:  ngrok http 5000
       Then set WEBHOOK_BASE_URL=https://<your-ngrok-id>.ngrok.io in .env
    3. In a second terminal, start the webhook server:  python app.py
    4. Run this script to kick off the calls.
"""

from __future__ import annotations

import logging
import os
import time

from twilio.rest import Client as TwilioClient

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_twilio = TwilioClient(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)


def _mask_phone(number: str) -> str:
    """Return a masked phone number, showing only the last 4 digits."""
    if len(number) >= 4:
        return "***" + number[-4:]
    return "****"

def make_call(call_number: int) -> str:
    """
    Initiate a single outbound call.
    Returns the Twilio CallSid.
    """
    logger.info("Initiating call #%d", call_number)

    call = _twilio.calls.create(
        to=config.TARGET_PHONE_NUMBER,
        from_=config.TWILIO_PHONE_NUMBER,
        url=f"{config.WEBHOOK_BASE_URL}/answer",
        method="POST",
        record=True,
        recording_channels=config.RECORDING_CHANNELS,
        status_callback=f"{config.WEBHOOK_BASE_URL}/recording_done",
        status_callback_method="POST",
        status_callback_event=["completed"],
        timeout=30,
    )

    call_sid: str = call.sid
    logger.info("Call #%d created — status: %s", call_number, call.status)
    return call_sid


def wait_for_call_completion(call_sid: str, poll_interval: int = 10, max_wait: int = 300) -> str:
    """
    Poll Twilio until the call reaches a terminal status.
    Returns the final status string.
    """
    deadline = time.time() + max_wait
    while time.time() < deadline:
        call = _twilio.calls(call_sid).fetch()
        logger.info("[%s] Call status: %s", call_sid, call.status)
        if call.status in ("completed", "failed", "busy", "no-answer", "canceled"):
            return call.status
        time.sleep(poll_interval)
    logger.warning("[%s] Timed out waiting for call completion.", call_sid)
    return "timeout"


def run_all_calls(num_calls: int = config.NUM_CALLS, delay_between: int = 60) -> None:
    """
    Make *num_calls* sequential calls to the target number.
    Waits *delay_between* seconds between calls to avoid flooding.
    """
    os.makedirs(config.AUDIO_DIR, exist_ok=True)
    os.makedirs(config.TRANSCRIPT_DIR, exist_ok=True)

    logger.info(
        "Starting campaign: %d calls (delay=%ds)",
        num_calls, delay_between
    )

    results: list[dict] = []

    for i in range(1, num_calls + 1):
        try:
            call_sid = make_call(i)
            final_status = wait_for_call_completion(call_sid)
            results.append({"call_number": i, "call_sid": call_sid, "status": final_status})
            logger.info("Call #%d finished — status: %s", i, final_status)
        except Exception:
            logger.exception("Error on call #%d", i)
            results.append({"call_number": i, "call_sid": "ERROR", "status": "error"})

        if i < num_calls:
            logger.info("Waiting %d seconds before next call…", delay_between)
            time.sleep(delay_between)

    # Summary
    logger.info("\n%s\nCALL CAMPAIGN SUMMARY\n%s", "=" * 50, "=" * 50)
    for r in results:
        logger.info("  Call #%d  status: %s", r["call_number"], r["status"])
    logger.info("=" * 50)
    logger.info("Transcripts → %s/", config.TRANSCRIPT_DIR)
    logger.info("Recordings  → %s/", config.AUDIO_DIR)
    logger.info("Bug report  → %s", config.BUG_REPORT_PATH)


if __name__ == "__main__":
    run_all_calls()
