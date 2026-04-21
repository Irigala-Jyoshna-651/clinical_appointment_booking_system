# Clinical Appointment Booking System

Real-time multilingual voice AI agent for booking, rescheduling, cancelling, and following up on clinical appointments in English, Hindi, Tamil, Telugu, and Kannada.

## What is included

- FastAPI backend with REST and WebSocket interfaces
- Browser demo client at `/demo`
- Real-time voice turn pipeline: STT -> language detection -> reasoning -> tool orchestration -> TTS
- Appointment lifecycle support: book, reschedule, cancel, check availability
- Session memory with Redis fallback
- Persistent patient memory and interaction history
- Outbound campaign endpoint for reminders and follow-ups
- Latency measurement for each stage and total turn time
- Docker setup, sample data, and tests

## Project structure

```text
backend/
  api/
  config.py
  dependencies.py
  main.py
  schemas.py
agent/
  prompts.py
  service.py
  tools.py
memory/
  persistent_memory.py
  session_memory.py
scheduler/
  appointment_engine.py
services/
  language_detection.py
  latency.py
  localization.py
  speech_to_text.py
  text_to_speech.py
data/
docs/
tests/
```

## Architecture

The runtime flow is:

```text
Voice Input
  -> WebSocket
  -> STT
  -> Language Detection
  -> Agent Reasoning
  -> Appointment Tools
  -> Memory Update
  -> TTS
  -> Audio Response
```

The Mermaid diagram is in [docs/architecture.md](/c:/Users/DELL/Downloads/clinical_appointment_booking_system/docs/architecture.md).

## Setup

### Local

1. Create a virtual environment and install dependencies.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

2. Start Redis if you want external memory storage. The app still runs without Redis using local fallback memory.

3. Run the API.

```bash
uvicorn backend.main:app --reload
```

4. Open:

- `GET /` for health
- `POST /campaigns/outbound` for outbound reminder generation
- `WS /ws/voice` for real-time voice turns
- `/demo` for the browser voice demo

### Docker

```bash
copy .env.example .env
docker compose up --build
```

## Environment variables

See `.env.example`.

- `OPENAI_API_KEY`: optional. When set, the agent first tries LLM JSON reasoning and falls back to rules if unavailable.
- `STT_PROVIDER`: use `mock` for offline text/base64 testing or `openai` for real audio transcription.
- `TTS_PROVIDER`: use `mock` for demoable WAV tone output or `openai` for real generated speech.
- `STT_MODEL`: defaults to `gpt-4o-mini-transcribe`
- `TTS_MODEL`: defaults to `gpt-4o-mini-tts`
- `TTS_VOICE`: defaults to `alloy`
- `REDIS_URL`: Redis connection string for session and persistent memory.
- `LATENCY_TARGET_MS`: target first-response latency in milliseconds.

For real OpenAI audio:

```env
OPENAI_API_KEY=your_key_here
STT_PROVIDER=openai
TTS_PROVIDER=openai
STT_MODEL=gpt-4o-mini-transcribe
TTS_MODEL=gpt-4o-mini-tts
TTS_VOICE=alloy
```

## API usage

### Health check

```http
GET /
```

### Outbound campaign

```http
POST /campaigns/outbound
Content-Type: application/json

{
  "patient_id": "pat-001",
  "session_id": "sess-campaign-1",
  "campaign_type": "reminder"
}
```

### Voice WebSocket

Send JSON messages to `/ws/voice`.

Example booking turn:

```json
{
  "type": "text",
  "session_id": "sess-100",
  "patient_id": "pat-001",
  "transcript": "Book appointment with cardiologist tomorrow at 10 am"
}
```

Example Hindi turn:

```json
{
  "type": "text",
  "session_id": "sess-101",
  "patient_id": "pat-001",
  "transcript": "मुझे कल हृदय रोग विशेषज्ञ से 10 am पर appointment book करनी है"
}
```

Example Tamil turn:

```json
{
  "type": "text",
  "session_id": "sess-102",
  "patient_id": "pat-002",
  "transcript": "நாளை குழந்தை மருத்துவருடன் 11 am appointment book செய்ய வேண்டும்"
}
```

The server responds with:

- normalized transcript
- detected language
- response text
- synthesized mock audio as base64
- selected action
- latency breakdown by stage
- updated context and appointment data

### Browser demo

Open `http://localhost:8000/demo`.

- Connect the socket
- Send typed prompts or record voice in the browser
- Play returned audio responses
- Trigger a reminder campaign from the same UI

## Memory design

### Session memory

- Keyed by `session_id`
- Stores current intent, collected fields, and latest appointment reference
- Uses Redis with TTL and in-process fallback

### Persistent memory

- Keyed by `patient_id`
- Stores preferred language, preferred hospital, appointment history, and interaction history
- Persists in `data/patients.json` and `data/interactions.json`
- Mirrors to Redis when available

## Multilingual behavior

The assistant is designed to respond in the same language the patient is currently speaking.

- English input -> English response
- Hindi input -> Hindi response
- Tamil input -> Tamil response
- Telugu input -> Telugu response
- Kannada input -> Kannada response

Language is determined per turn by the language detection stage. The patient's `preferred_language` in persistent memory is used only as a fallback when the current utterance is unclear or too short to detect reliably.

## Latency measurement

Each turn logs timing for:

- `stt`
- `language_detection`
- `reasoning`
- `tool_execution`
- `tts`
- `total`

The target is `LATENCY_TARGET_MS`, default `450 ms`.

With mock STT/TTS and in-process logic, the local code path is typically well under the target. Real provider latency will depend on network and model selection.

## Scheduling logic

- Prevents double booking for the same doctor, date, and slot
- Rejects missing booking fields
- Supports automatic fallback to the patient's latest active appointment for cancel/reschedule
- Suggests alternative open slots when a conflict happens

## Testing

Run:

```bash
pytest
```

Current automated tests cover:

- successful booking
- conflict detection
- rescheduling
- cancellation

## Trade-offs

- Mock STT/TTS keep the system demoable offline and preserve the architecture needed for production adapters.
- OpenAI-backed STT/TTS adapters are wired in and selected via environment variables.
- Rule-based multilingual reasoning provides deterministic baseline behavior; optional LLM reasoning enhances flexibility when `OPENAI_API_KEY` is configured.
- JSON persistence is simple for assignment delivery, while interfaces are clean enough to replace with PostgreSQL later.

## Known limitations

- Real telephony and streaming audio chunk handling are not included yet; the WebSocket API currently processes complete user turns.
- Language detection is heuristic rather than model-based.
- The current WebSocket flow processes one recorded audio turn at a time rather than true chunked streaming.
- Real latency under production STT/TTS providers must be benchmarked in deployment.
