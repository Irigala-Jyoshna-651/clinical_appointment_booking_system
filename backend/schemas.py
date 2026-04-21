from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


LanguageCode = Literal["en", "hi", "ta", "te", "kn"]
IntentName = Literal["book", "cancel", "reschedule", "check_availability", "smalltalk", "unknown"]


class VoiceChunk(BaseModel):
    type: Literal["audio", "text", "ping"] = "audio"
    session_id: str
    patient_id: str
    audio_base64: str | None = None
    transcript: str | None = None
    timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolPayload(BaseModel):
    doctor_specialty: str | None = None
    doctor_name: str | None = None
    date: str | None = None
    time: str | None = None
    appointment_id: str | None = None


class AgentDecision(BaseModel):
    intent: IntentName
    language: LanguageCode
    confidence: float = 0.0
    response_text: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    tool_payload: ToolPayload = Field(default_factory=ToolPayload)
    context_updates: dict[str, Any] = Field(default_factory=dict)


class AppointmentRecord(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    doctor_name: str
    specialty: str
    hospital: str
    date: str
    time: str
    status: Literal["booked", "cancelled", "rescheduled"]
    created_at: str


class DoctorSchedule(BaseModel):
    doctor_id: str
    doctor_name: str
    specialty: str
    hospital: str
    availability: dict[str, list[str]]


class VoiceResponse(BaseModel):
    type: Literal["agent_response"] = "agent_response"
    session_id: str
    patient_id: str
    transcript: str
    detected_language: LanguageCode
    response_text: str
    audio_base64: str
    action: str
    latency_ms: dict[str, float]
    context: dict[str, Any] = Field(default_factory=dict)
    appointment: AppointmentRecord | None = None
    suggestions: list[str] = Field(default_factory=list)


class OutboundCampaignRequest(BaseModel):
    patient_id: str
    session_id: str
    campaign_type: Literal["reminder", "follow_up", "vaccination"]
    message: str | None = None
    language: LanguageCode | None = None


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
