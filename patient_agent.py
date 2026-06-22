"""
patient_agent.py — GPT-4o powered patient persona.

The agent maintains conversation history and generates realistic patient
responses for each turn of the call.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import openai

import config

logger = logging.getLogger(__name__)

# System prompt that instructs the LLM to roleplay as a patient
_SYSTEM_PROMPT = f"""You are roleplaying as {config.PATIENT_NAME}, a real patient calling a
medical scheduling / healthcare phone agent.

Patient details:
  • Name        : {config.PATIENT_NAME}
  • Date of birth: {config.PATIENT_DOB}
  • Insurance   : {config.PATIENT_INSURANCE}
  • Reason      : {config.PATIENT_REASON}

Behavioral rules:
1. Speak naturally, like a real person on a phone call — short sentences, occasional
   filler words (um, uh, let me see…), realistic pauses via ellipsis.
2. Never break character or mention AI, GPT, or scripts.
3. If the agent asks for info (name, DOB, insurance, reason), provide it naturally.
4. If the agent seems confused, mishears you, or gives wrong info, note it (this helps
   detect bugs) and try again politely.
5. If the agent asks something unclear or non-sensical, express polite confusion:
   "Sorry, I'm not sure I understand…"
6. To end the call gracefully, say EXACTLY: "Thank you, goodbye!"
7. Keep each response under 40 words.
8. Respond ONLY with the words you would speak — no narration, no stage directions.
"""


class PatientAgent:
    """Stateful conversational agent that plays the role of a patient."""

    def __init__(self, call_sid: str) -> None:
        self.call_sid = call_sid
        self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        self.history: list[dict[str, str]] = []
        self._turn = 0
        logger.info("[%s] PatientAgent initialised for %s", call_sid, config.PATIENT_NAME)

    # ── Public API ─────────────────────────────────────────────────────────────

    def respond(self, agent_text: str) -> str:
        """Given what the remote agent just said, return the patient's reply."""
        self._turn += 1
        self.history.append({"role": "user", "content": agent_text})

        completion = self.client.chat.completions.create(
            model=config.OPENAI_CHAT_MODEL,
            messages=[{"role": "system", "content": _SYSTEM_PROMPT}] + self.history,
            temperature=0.7,
            max_tokens=80,
        )
        reply: str = completion.choices[0].message.content.strip()
        self.history.append({"role": "assistant", "content": reply})

        logger.debug("[%s] Turn %d — agent: %r → patient: %r", self.call_sid, self._turn,
                     agent_text, reply)
        return reply

    def opening_statement(self) -> str:
        """Generate the first thing the patient says when the call connects."""
        prompt = (
            "The call just connected. As the patient, say a natural greeting and "
            "briefly state why you are calling. Keep it under 25 words."
        )
        self.history.append({"role": "user", "content": prompt})

        completion = self.client.chat.completions.create(
            model=config.OPENAI_CHAT_MODEL,
            messages=[{"role": "system", "content": _SYSTEM_PROMPT}] + self.history,
            temperature=0.8,
            max_tokens=60,
        )
        reply: str = completion.choices[0].message.content.strip()
        self.history.append({"role": "assistant", "content": reply})
        logger.info("[%s] Opening statement: %r", self.call_sid, reply)
        return reply

    def should_end_call(self) -> bool:
        """Return True when the patient has said goodbye or the turn limit is reached."""
        if self._turn > 20:
            return True
        if self.history:
            last = self.history[-1].get("content", "")
            return "goodbye" in last.lower()
        return False

    def export_transcript(self) -> list[dict[str, Any]]:
        """Return the full conversation as a list of turn dicts."""
        turns = []
        for i in range(0, len(self.history) - 1, 2):
            turns.append({
                "turn": i // 2 + 1,
                "agent": self.history[i]["content"],
                "patient": self.history[i + 1]["content"] if i + 1 < len(self.history) else "",
            })
        return turns

    def save_transcript(self, path: str) -> None:
        """Persist the conversation transcript to *path* as JSON."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "call_sid": self.call_sid,
            "patient_name": config.PATIENT_NAME,
            "turns": self.export_transcript(),
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        logger.info("[%s] Transcript saved → %s", self.call_sid, path)
