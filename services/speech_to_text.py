from __future__ import annotations

import base64
import io

from openai import OpenAI


class SpeechToTextService:
    def __init__(self, provider: str = "mock", api_key: str | None = None, model: str = "gpt-4o-mini-transcribe"):
        self.provider = provider
        self.model = model
        self.client = OpenAI(api_key=api_key) if api_key else None

    def transcribe(self, audio_base64: str | None, metadata: dict | None = None) -> str:
        metadata = metadata or {}
        if metadata.get("transcript"):
            return metadata["transcript"]
        if not audio_base64:
            return ""
        if self.provider == "openai" and self.client:
            transcript = self._transcribe_with_openai(audio_base64, metadata)
            if transcript:
                return transcript
        try:
            decoded = base64.b64decode(audio_base64).decode("utf-8")
            return decoded
        except Exception:
            return "Unable to transcribe audio input."

    def _transcribe_with_openai(self, audio_base64: str, metadata: dict) -> str | None:
        try:
            audio_bytes = base64.b64decode(audio_base64)
            suffix = metadata.get("audio_format", "webm")
            buffer = io.BytesIO(audio_bytes)
            buffer.name = f"input.{suffix}"
            response = self.client.audio.transcriptions.create(
                file=buffer,
                model=self.model,
                response_format="text",
            )
            if hasattr(response, "text"):
                return response.text
            if isinstance(response, str):
                return response
            return None
        except Exception:
            return None
