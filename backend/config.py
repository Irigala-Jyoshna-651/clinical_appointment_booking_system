from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Clinical Appointment Booking System", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    memory_backend: str = Field(default="hybrid", alias="MEMORY_BACKEND")
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    stt_provider: str = Field(default="mock", alias="STT_PROVIDER")
    tts_provider: str = Field(default="mock", alias="TTS_PROVIDER")
    stt_model: str = Field(default="gpt-4o-mini-transcribe", alias="STT_MODEL")
    tts_model: str = Field(default="gpt-4o-mini-tts", alias="TTS_MODEL")
    tts_voice: str = Field(default="alloy", alias="TTS_VOICE")
    latency_target_ms: int = Field(default=450, alias="LATENCY_TARGET_MS")
    session_ttl_seconds: int = Field(default=1800, alias="SESSION_TTL_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
