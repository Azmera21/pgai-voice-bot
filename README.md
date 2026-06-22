# pgai-voice-bot

A Python voice bot that calls the Pretty Good AI healthcare scheduling agent
(+1-805-439-8008), converses like a real patient, records every call, transcribes
the audio with OpenAI Whisper, and automatically logs bugs found in the target
agent's behaviour.

---

## Repository layout

```
pgai-voice-bot/
├─ main.py           # Orchestrates outbound calls (run this)
├─ app.py            # Flask webhook server (Twilio calls this during a live call)
├─ patient_agent.py  # GPT-4o powered patient persona
├─ transcriber.py    # Downloads Twilio recordings + transcribes with Whisper
├─ tts.py            # OpenAI TTS helper
├─ bug_reporter.py   # GPT-4o bug analysis + BUGS.md writer
├─ config.py         # All configuration (loaded from .env)
├─ requirements.txt
├─ .env.example      # Copy → .env and fill in your credentials
├─ README.md
├─ ARCHITECTURE.md
├─ BUGS.md           # Auto-generated bug report (created on first run)
└─ calls/
   ├─ audio/         # Downloaded MP3 recordings
   └─ transcripts/   # JSON transcripts
```

---

## Quick-start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env — add your Twilio and OpenAI API keys
```

You need:

| Key | Where to get it |
|-----|-----------------|
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | [twilio.com/console](https://www.twilio.com/console) |
| `TWILIO_PHONE_NUMBER` | Buy a number in the Twilio console |
| `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `WEBHOOK_BASE_URL` | Your public ngrok/tunnel URL (see step 3) |

### 3. Expose the webhook server

```bash
# Terminal 1 — start the Flask app
python app.py

# Terminal 2 — open a public tunnel
ngrok http 5000
# Copy the https URL (e.g. https://abc123.ngrok.io) into WEBHOOK_BASE_URL in .env
```

### 4. Run the calls

```bash
# Terminal 3
python main.py
```

This will make `NUM_CALLS` (default 10) sequential calls to +1-805-439-8008.
Between calls there is a configurable delay (`delay_between`, default 60 s) to
avoid rate-limiting.

After each call completes:

- The recording is downloaded to `calls/audio/`
- Whisper transcribes it → `calls/transcripts/`
- GPT-4o analyses the transcript for bugs → appended to `BUGS.md`

---

## Configuration reference

All settings live in `.env` (see `.env.example` for the full list).

| Variable | Default | Description |
|---|---|---|
| `TARGET_PHONE_NUMBER` | `+18054398008` | Number to call |
| `NUM_CALLS` | `10` | Total calls to make |
| `OPENAI_CHAT_MODEL` | `gpt-4o` | LLM for patient persona + bug analysis |
| `OPENAI_TTS_VOICE` | `nova` | TTS voice (`nova` is warm/female) |
| `PATIENT_NAME` | `Sarah Johnson` | Patient persona name |
| `PATIENT_DOB` | `March 14, 1985` | Patient date of birth |
| `PATIENT_INSURANCE` | `BlueCross BlueShield PPO` | Insurance information |
| `RECORDING_CHANNELS` | `dual` | `dual` records both call legs separately |

---

## How it works

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

---

## Output artifacts

| File | Description |
|---|---|
| `calls/audio/<call_sid>_recording.mp3` | Dual-channel call recording |
| `calls/transcripts/<call_sid>.json` | Whisper transcript + metadata |
| `calls/transcripts/<call_sid>_conversation.json` | Turn-by-turn conversation log |
| `BUGS.md` | Markdown bug report (one section per call) |
| `calls/bugs.json` | Machine-readable bug log |

---

## License

MIT
