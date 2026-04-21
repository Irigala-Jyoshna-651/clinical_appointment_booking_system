from __future__ import annotations

import base64
import io
import math
import wave

from openai import OpenAI


class TextToSpeechService:
    def __init__(
        self,
        provider: str = "mock",
        api_key: str | None = None,
        model: str = "gpt-4o-mini-tts",
        voice: str = "alloy",
    ):
        self.provider = provider
        self.model = model
        self.voice = voice
        self.client = OpenAI(api_key=api_key) if api_key else None

    def synthesize(self, text: str, language: str = "en") -> str:
        if self.provider == "openai" and self.client:
            speech = self._synthesize_with_openai(text=text, language=language)
            if speech:
                return speech
        return self._synthesize_mock_tone(language=language)

    def _synthesize_with_openai(self, text: str, language: str) -> str | None:
        try:
            instructions = {
                "en": "Speak clearly in English for a clinical appointment assistant.",
                "hi": "Speak clearly in Hindi for a clinical appointment assistant.",
                "ta": "Speak clearly in Tamil for a clinical appointment assistant.",
            }
            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
                response_format="wav",
                instructions=instructions.get(language, instructions["en"]),
            )
            audio_bytes = response.read() if hasattr(response, "read") else bytes(response)
            return base64.b64encode(audio_bytes).decode("utf-8")
        except Exception:
            return None

    @staticmethod
    def _synthesize_mock_tone(language: str) -> str:
        sample_rate = 16000
        duration_seconds = 0.45
        total_samples = int(sample_rate * duration_seconds)
        frequency_map = {"en": 440, "hi": 523, "ta": 587}
        frequency = frequency_map.get(language, 440)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            frames = bytearray()
            for index in range(total_samples):
                envelope = 1.0 - (index / total_samples)
                sample = int(12000 * envelope * math.sin(2 * math.pi * frequency * index / sample_rate))
                frames.extend(sample.to_bytes(2, byteorder="little", signed=True))
            wav_file.writeframes(bytes(frames))
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
