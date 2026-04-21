from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from agent.prompts import SYSTEM_PROMPT
from agent.tools import AppointmentTools
from backend.schemas import AgentDecision, OutboundCampaignRequest, VoiceChunk, VoiceResponse
from services.latency import StageTimer
from services.localization import Localizer


class VoiceAppointmentAgent:
    def __init__(
        self,
        session_memory,
        persistent_memory,
        appointment_engine,
        language_detector,
        stt_service,
        tts_service,
        openai_api_key: str | None,
        openai_model: str,
        latency_target_ms: int,
    ):
        self.session_memory = session_memory
        self.persistent_memory = persistent_memory
        self.appointment_engine = appointment_engine
        self.language_detector = language_detector
        self.stt_service = stt_service
        self.tts_service = tts_service
        self.localizer = Localizer()
        self.tools = AppointmentTools(appointment_engine=appointment_engine)
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.openai_model = openai_model
        self.latency_target_ms = latency_target_ms

    async def handle_voice_turn(self, chunk: VoiceChunk) -> VoiceResponse:
        timer = StageTimer(target_ms=self.latency_target_ms)
        session_context = self.session_memory.get(chunk.session_id)
        patient_profile = self.persistent_memory.get_patient_profile(chunk.patient_id)

        with timer.stage("stt"):
            transcript = chunk.transcript or self.stt_service.transcribe(chunk.audio_base64, metadata=chunk.metadata)

        with timer.stage("language_detection"):
            language = self.language_detector.detect(transcript, fallback=patient_profile.get("preferred_language", "en"))

        with timer.stage("reasoning"):
            decision = self._decide(transcript, language, session_context, patient_profile)

        with timer.stage("tool_execution"):
            tool_result = self._execute(decision, chunk.patient_id, session_context, patient_profile)

        updated_context = {**session_context, **decision.context_updates, **(tool_result.context_updates or {})}
        updated_context["last_user_transcript"] = transcript
        updated_context["last_language"] = language
        if tool_result.appointment:
            updated_context["last_appointment_id"] = tool_result.appointment["id"]
            self.persistent_memory.record_appointment(chunk.patient_id, tool_result.appointment)

        self.session_memory.set(chunk.session_id, updated_context)

        response_text = self.localizer.render(
            language=language,
            base_text=tool_result.message,
            patient_profile=patient_profile,
            action=tool_result.action,
            suggestions=tool_result.suggestions,
        )

        with timer.stage("tts"):
            audio_base64 = self.tts_service.synthesize(response_text, language=language)

        self.persistent_memory.record_interaction(
            patient_id=chunk.patient_id,
            interaction={
                "session_id": chunk.session_id,
                "user_text": transcript,
                "agent_text": response_text,
                "language": language,
                "action": tool_result.action,
                "latency_ms": timer.snapshot(),
            },
        )

        return VoiceResponse(
            session_id=chunk.session_id,
            patient_id=chunk.patient_id,
            transcript=transcript,
            detected_language=language,
            response_text=response_text,
            audio_base64=audio_base64,
            action=tool_result.action,
            latency_ms=timer.snapshot(include_total=True),
            context=updated_context,
            appointment=tool_result.appointment,
            suggestions=tool_result.suggestions,
        )

    async def handle_outbound_campaign(self, payload: OutboundCampaignRequest) -> VoiceResponse:
        patient_profile = self.persistent_memory.get_patient_profile(payload.patient_id)
        language = payload.language or patient_profile.get("preferred_language", "en")
        default_messages = {
            "reminder": "This is a reminder about your upcoming appointment. You can ask me to reschedule or cancel it.",
            "follow_up": "This is your follow-up check-in call from the clinic. Do you want to book your next visit?",
            "vaccination": "This is a reminder that your vaccination is due. I can help book a slot now.",
        }
        response_text = self.localizer.render(
            language=language,
            base_text=payload.message or default_messages[payload.campaign_type],
            patient_profile=patient_profile,
            action=payload.campaign_type,
            suggestions=[],
        )
        audio_base64 = self.tts_service.synthesize(response_text, language=language)
        self.session_memory.set(
            payload.session_id,
            {"campaign_type": payload.campaign_type, "outbound": True, "last_language": language},
        )
        return VoiceResponse(
            session_id=payload.session_id,
            patient_id=payload.patient_id,
            transcript="",
            detected_language=language,
            response_text=response_text,
            audio_base64=audio_base64,
            action=payload.campaign_type,
            latency_ms={"tts": 0.0, "total": 0.0},
            context={"campaign_type": payload.campaign_type, "outbound": True},
            appointment=None,
            suggestions=[],
        )

    async def close_session(self, websocket: Any) -> None:
        _ = websocket

    def _decide(self, transcript: str, language: str, session_context: dict, patient_profile: dict) -> AgentDecision:
        if self.openai_client:
            llm_decision = self._decide_with_openai(transcript, language, session_context, patient_profile)
            if llm_decision:
                return llm_decision
        return self._decide_with_rules(transcript, language, session_context)

    def _decide_with_openai(self, transcript: str, language: str, session_context: dict, patient_profile: dict) -> AgentDecision | None:
        try:
            prompt = {
                "transcript": transcript,
                "language": language,
                "session_context": session_context,
                "patient_profile": patient_profile,
            }
            response = self.openai_client.responses.create(
                model=self.openai_model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
            )
            content = getattr(response, "output_text", "").strip()
            if not content:
                return None
            return AgentDecision.model_validate_json(content)
        except Exception:
            return None

    def _decide_with_rules(self, transcript: str, language: str, session_context: dict) -> AgentDecision:
        text = transcript.lower().strip()
        context_doctor = session_context.get("doctor_specialty")
        context_date = session_context.get("date")
        context_time = session_context.get("time")

        cancel_terms = [
            "cancel",
            "\u0930\u0926\u094d\u0926",
            "\u0bb0\u0ba4\u0bcd\u0ba4\u0bc1",
            "\u0c30\u0c26\u0d4d\u0c26\u0c41",
            "\u0cb0\u0ca6\u0ccd\u0ca6\u0cc1",
        ]
        reschedule_terms = [
            "reschedule",
            "move",
            "change",
            "\u092c\u0926\u0932",
            "\u0bae\u0bbe\u0bb1\u0bcd\u0bb1",
            "\u0c2e\u0c3e\u0c30\u0c4d\u0c1a",
            "\u0cac\u0ca6\u0cb2\u0cbe",
        ]
        availability_terms = [
            "available",
            "availability",
            "slot",
            "\u0909\u092a\u0932\u092c\u094d\u0927",
            "\u0b95\u0bbe\u0bb2\u0bbf",
            "\u0c05\u0c02\u0c26\u0c41\u0c2c\u0c3e\u0c1f\u0c41",
            "\u0cb2\u0cad\u0ccd\u0caf",
        ]
        booking_terms = [
            "book",
            "appointment",
            "doctor",
            "\u092e\u093f\u0932\u0928\u093e",
            "\u092c\u0941\u0915",
            "\u0bae\u0bb0\u0bc1\u0ba4\u0bcd\u0ba4\u0bc1\u0bb5\u0bb0\u0bcd",
            "\u0baa\u0bc1\u0b95\u0bcd",
            "\u0c21\u0c3e\u0c15\u0c4d\u0c1f\u0c30\u0c4d",
            "\u0c05\u0c2a\u0c3e\u0c2f\u0c3f\u0c02\u0c1f\u0c4d\u0c2e\u0c46\u0c02\u0c4d\u0c1f\u0c4d",
            "\u0c2c\u0c41\u0c15\u0c4d",
            "\u0cb5\u0cc8\u0ca6\u0ccd\u0caf",
            "\u0cac\u0cc1\u0c95\u0ccd",
        ]
        greeting_terms = ["hello", "hi", "namaste", "vanakkam", "namaskaram", "namaskara"]

        if any(word in text for word in cancel_terms):
            return AgentDecision(intent="cancel", language=language, confidence=0.88)

        if any(word in text for word in reschedule_terms):
            return AgentDecision(
                intent="reschedule",
                language=language,
                confidence=0.86,
                tool_payload={"date": self._extract_date(text) or context_date, "time": self._extract_time(text) or context_time},
            )

        if any(word in text for word in availability_terms):
            specialty = self._extract_specialty(text) or context_doctor
            date = self._extract_date(text) or context_date
            missing = [field for field, value in {"doctor_specialty": specialty, "date": date}.items() if not value]
            return AgentDecision(
                intent="check_availability",
                language=language,
                confidence=0.84,
                missing_fields=missing,
                tool_payload={"doctor_specialty": specialty, "date": date},
                context_updates={"doctor_specialty": specialty, "date": date},
            )

        if any(word in text for word in booking_terms):
            specialty = self._extract_specialty(text) or context_doctor
            date = self._extract_date(text) or context_date
            time = self._extract_time(text) or context_time
            missing = [field for field, value in {"doctor_specialty": specialty, "date": date, "time": time}.items() if not value]
            return AgentDecision(
                intent="book",
                language=language,
                confidence=0.9,
                missing_fields=missing,
                tool_payload={"doctor_specialty": specialty, "date": date, "time": time},
                context_updates={"doctor_specialty": specialty, "date": date, "time": time},
            )

        if any(word in text for word in greeting_terms):
            return AgentDecision(intent="smalltalk", language=language, confidence=0.75, response_text="How can I help with your appointment today?")

        if text and session_context.get("last_intent") == "book":
            specialty = self._extract_specialty(text) or context_doctor
            date = self._extract_date(text) or context_date
            time = self._extract_time(text) or context_time
            missing = [field for field, value in {"doctor_specialty": specialty, "date": date, "time": time}.items() if not value]
            return AgentDecision(
                intent="book",
                language=language,
                confidence=0.7,
                missing_fields=missing,
                tool_payload={"doctor_specialty": specialty, "date": date, "time": time},
                context_updates={"doctor_specialty": specialty, "date": date, "time": time},
            )

        return AgentDecision(intent="unknown", language=language, confidence=0.25, response_text="Please tell me if you want to book, reschedule, cancel, or check an appointment.")

    def _execute(self, decision: AgentDecision, patient_id: str, session_context: dict, patient_profile: dict):
        payload = decision.tool_payload.model_dump() if hasattr(decision.tool_payload, "model_dump") else dict(decision.tool_payload)

        if decision.intent == "smalltalk":
            from agent.models import ToolResult
            return ToolResult(action="smalltalk", message=decision.response_text or "How can I help with your appointment today?")

        if decision.intent == "unknown":
            from agent.models import ToolResult
            return ToolResult(action="clarify", message=decision.response_text or "Please repeat your request.")

        if decision.missing_fields:
            prompts = {
                "doctor_specialty": "Which doctor or specialty would you like to see?",
                "date": "Which date would you prefer?",
                "time": "What time works best for you?",
            }
            from agent.models import ToolResult
            missing_prompt = " ".join(prompts[field] for field in decision.missing_fields if field in prompts)
            return ToolResult(
                action="collect_details",
                message=missing_prompt,
                context_updates={"last_intent": decision.intent, **decision.context_updates},
            )

        if decision.intent == "check_availability":
            return self.tools.check_availability(payload.get("doctor_specialty"), payload.get("date"))

        if decision.intent == "book":
            return self.tools.book(
                patient_id=patient_id,
                specialty=payload.get("doctor_specialty"),
                doctor_name=payload.get("doctor_name"),
                date=payload.get("date"),
                time=payload.get("time"),
            )

        if decision.intent == "cancel":
            appointment_id = payload.get("appointment_id") or session_context.get("last_appointment_id")
            return self.tools.cancel(patient_id=patient_id, appointment_id=appointment_id)

        if decision.intent == "reschedule":
            appointment_id = payload.get("appointment_id") or session_context.get("last_appointment_id")
            return self.tools.reschedule(
                patient_id=patient_id,
                appointment_id=appointment_id,
                date=payload.get("date"),
                time=payload.get("time"),
            )

        from agent.models import ToolResult
        return ToolResult(action="clarify", message="Please repeat your request.")

    @staticmethod
    def _extract_specialty(text: str) -> str | None:
        specialties = ["cardiologist", "dermatologist", "dentist", "pediatrician", "neurologist", "orthopedic"]
        multilingual_map = {
            "heart": "cardiologist",
            "\u0924\u094d\u0935\u091a\u093e": "dermatologist",
            "\u0926\u093f\u0932": "cardiologist",
            "\u0b95\u0bc1\u0bb4\u0ba8\u0bcd\u0ba4\u0bc8": "pediatrician",
            "\u0baa\u0bb2\u0bcd": "dentist",
            "\u0c17\u0c41\u0c02\u0c21\u0c46": "cardiologist",
            "\u0c1a\u0c30\u0c4d\u0c2e": "dermatologist",
            "\u0c2a\u0c3f\u0c32\u0c4d\u0c32\u0cb2": "pediatrician",
            "\u0ca6\u0c82\u0ca4": "dentist",
            "skin": "dermatologist",
        }
        for item in specialties:
            if item in text:
                return item
        for key, value in multilingual_map.items():
            if key in text:
                return value
        return None

    @staticmethod
    def _extract_date(text: str) -> str | None:
        if (
            "today" in text
            or "\u0906\u091c" in text
            or "\u0b87\u0ba9\u0bcd\u0bb1\u0bc1" in text
            or "\u0c08\u0c30\u0c4b\u0c1c\u0c41" in text
            or "\u0c87\u0cb5\u0ca4\u0ccd\u0ca4\u0cc1" in text
        ):
            return "today"
        if (
            "tomorrow" in text
            or "\u0915\u0932" in text
            or "\u0ba8\u0bbe\u0bb3\u0bc8" in text
            or "\u0c30\u0c47\u0c2a\u0c41" in text
            or "\u0ca8\u0cbe\u0cb3\u0cc6" in text
        ):
            return "tomorrow"
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for weekday in weekdays:
            if weekday in text:
                return weekday
        return None

    @staticmethod
    def _extract_time(text: str) -> str | None:
        known = ["9 am", "10 am", "11 am", "12 pm", "1 pm", "2 pm", "3 pm", "4 pm", "10:30 am", "2:00 pm", "4:30 pm"]
        for item in known:
            if item in text:
                return item
        return None
