# Architecture — pgai-voice-bot

## Overview

The system makes automated outbound calls to the Pretty Good AI healthcare
scheduling agent (+1-805-439-8008), simulates a real patient conversation,
records and transcribes every call, and logs bugs observed in the target agent.

---

## Component diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Developer machine                                              │
│                                                                 │
│  ┌──────────┐    HTTP REST API    ┌────────────────────────┐   │
│  │ main.py  │ ──────────────────► │  Twilio Cloud          │   │
│  │(launcher)│                     │  (outbound call API)   │   │
│  └──────────┘                     └────────────┬───────────┘   │
│                                                │               │
│  ┌──────────┐  webhooks (TwiML)   ┌────────────▼───────────┐   │
│  │  app.py  │ ◄────────────────── │  ngrok tunnel          │   │
│  │ (Flask)  │ ──────────────────► │  (public HTTPS URL)    │   │
│  └────┬─────┘                     └────────────────────────┘   │
│       │                                                         │
│  ┌────▼──────────────────────────────────────────────────────┐ │
│  │  patient_agent.py                                         │ │
│  │  • Maintains per-call conversation history                │ │
│  │  • Calls OpenAI GPT-4o to generate patient responses      │ │
│  │  • Detects call-end condition                             │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  tts.py          │  │  transcriber.py  │                    │
│  │  OpenAI TTS      │  │  • Polls Twilio  │                    │
│  │  (tts-1 / nova)  │  │    for recording │                    │
│  └──────────────────┘  │  • Downloads MP3 │                    │
│                         │  • Whisper STT   │                    │
│                         └──────────────────┘                   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  bug_reporter.py                                         │  │
│  │  • Sends transcript to GPT-4o for QA analysis            │  │
│  │  • Classifies bugs by category and severity              │  │
│  │  • Appends findings to BUGS.md + calls/bugs.json         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Call flow (sequence diagram)

```
main.py          Twilio          Target agent        app.py (Flask)
   │                │                   │                   │
   │─ calls.create ►│                   │                   │
   │                │─── dials ────────►│                   │
   │                │◄── answered ──────│                   │
   │                │─── POST /answer ──────────────────────►│
   │                │◄── TwiML (Record + Gather) ────────────│
   │                │─── plays opening ─►│                   │
   │                │◄── agent speaks ──│                   │
   │                │─── POST /gather ──────────────────────►│
   │                │                   │  PatientAgent.respond()
   │                │◄── TwiML (Gather) ─────────────────────│
   │                │─── plays reply ───►│                   │
   │                │   … (N turns) …   │                   │
   │                │─── hangup ────────►│                   │
   │                │─── POST /recording_done ──────────────►│
   │                │                   │  transcriber.process_call()
   │                │                   │  bug_reporter.report_bugs()
```

---

## Technology choices

| Concern | Technology | Rationale |
|---|---|---|
| Telephony | Twilio Programmable Voice | Industry-standard, excellent Python SDK, dual-channel recording |
| Webhook server | Flask 3 | Lightweight, minimal boilerplate for TwiML endpoints |
| Patient persona | OpenAI GPT-4o | Best conversational quality for natural patient simulation |
| Text-to-speech | OpenAI TTS (nova voice) | Natural-sounding, low-latency, no extra service needed |
| Speech-to-text | OpenAI Whisper | State-of-the-art accuracy, same API key as LLM |
| Bug detection | GPT-4o with JSON output | Flexible, context-aware QA without hardcoded rules |
| Tunnel | ngrok | Simple localhost exposure; swap for Cloudflare Tunnel in production |

---

## Data flow

```
Twilio MP3 recording
        │
        ▼
transcriber.download_recording()   →  calls/audio/<sid>_recording.mp3
        │
        ▼
transcriber.transcribe_audio()     →  raw text
        │
        ▼
transcriber.save_transcript()      →  calls/transcripts/<sid>.json
        │
        ▼
bug_reporter.analyse_transcript()  →  JSON list of bug objects
        │
        ▼
bug_reporter.append_to_markdown()  →  BUGS.md
bug_reporter.append_to_json_log()  →  calls/bugs.json
```

---

## Scalability notes

- Calls are made sequentially with a configurable delay to avoid Twilio
  rate-limits and to give each call a clean recording.
- The Flask app handles each Twilio webhook in a single thread (default).
  For concurrent calls, switch to `gunicorn --workers 4 app:app`.
- Call state is held in-process memory (`_CALLS` dict in `app.py`).
  For multi-process deployments, replace with Redis.
