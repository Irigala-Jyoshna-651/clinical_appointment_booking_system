from __future__ import annotations

from agent.models import ToolResult


class AppointmentTools:
    def __init__(self, appointment_engine):
        self.appointment_engine = appointment_engine

    def check_availability(self, specialty: str | None, date: str | None) -> ToolResult:
        result = self.appointment_engine.check_availability(specialty=specialty, date=date)
        return ToolResult(
            action="check_availability",
            message=result["message"],
            suggestions=result.get("suggestions", []),
            context_updates={"last_availability_search": {"specialty": specialty, "date": date}},
        )

    def book(self, patient_id: str, specialty: str | None, doctor_name: str | None, date: str | None, time: str | None) -> ToolResult:
        result = self.appointment_engine.book_appointment(
            patient_id=patient_id,
            specialty=specialty,
            doctor_name=doctor_name,
            date=date,
            time=time,
        )
        return ToolResult(
            action="book",
            message=result["message"],
            appointment=result.get("appointment"),
            suggestions=result.get("suggestions", []),
            context_updates={"last_intent": "book"},
        )

    def cancel(self, patient_id: str, appointment_id: str | None = None) -> ToolResult:
        result = self.appointment_engine.cancel_appointment(patient_id=patient_id, appointment_id=appointment_id)
        return ToolResult(
            action="cancel",
            message=result["message"],
            appointment=result.get("appointment"),
            suggestions=result.get("suggestions", []),
            context_updates={"last_intent": "cancel"},
        )

    def reschedule(self, patient_id: str, date: str | None, time: str | None, appointment_id: str | None = None) -> ToolResult:
        result = self.appointment_engine.reschedule_appointment(
            patient_id=patient_id,
            appointment_id=appointment_id,
            new_date=date,
            new_time=time,
        )
        return ToolResult(
            action="reschedule",
            message=result["message"],
            appointment=result.get("appointment"),
            suggestions=result.get("suggestions", []),
            context_updates={"last_intent": "reschedule"},
        )
