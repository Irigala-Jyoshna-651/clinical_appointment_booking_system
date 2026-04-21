from functools import lru_cache

from agent.service import VoiceAppointmentAgent
from backend.config import get_settings
from memory.persistent_memory import PersistentMemoryStore
from memory.session_memory import SessionMemoryStore
from scheduler.appointment_engine import AppointmentEngine
from services.language_detection import LanguageDetector
from services.speech_to_text import SpeechToTextService
from services.text_to_speech import TextToSpeechService


@lru_cache
def get_session_memory() -> SessionMemoryStore:
    settings = get_settings()
    return SessionMemoryStore(redis_url=settings.redis_url, ttl_seconds=settings.session_ttl_seconds)


@lru_cache
def get_persistent_memory() -> PersistentMemoryStore:
    settings = get_settings()
    return PersistentMemoryStore(redis_url=settings.redis_url, data_dir=settings.data_dir)


@lru_cache
def get_appointment_engine() -> AppointmentEngine:
    settings = get_settings()
    return AppointmentEngine(data_dir=settings.data_dir)


@lru_cache
def get_language_detector() -> LanguageDetector:
    return LanguageDetector()


@lru_cache
def get_stt_service() -> SpeechToTextService:
    settings = get_settings()
    return SpeechToTextService(
        provider=settings.stt_provider,
        api_key=settings.openai_api_key,
        model=settings.stt_model,
    )


@lru_cache
def get_tts_service() -> TextToSpeechService:
    settings = get_settings()
    return TextToSpeechService(
        provider=settings.tts_provider,
        api_key=settings.openai_api_key,
        model=settings.tts_model,
        voice=settings.tts_voice,
    )


@lru_cache
def get_agent() -> VoiceAppointmentAgent:
    settings = get_settings()
    return VoiceAppointmentAgent(
        session_memory=get_session_memory(),
        persistent_memory=get_persistent_memory(),
        appointment_engine=get_appointment_engine(),
        language_detector=get_language_detector(),
        stt_service=get_stt_service(),
        tts_service=get_tts_service(),
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
        latency_target_ms=settings.latency_target_ms,
    )
