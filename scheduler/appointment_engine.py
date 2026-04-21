from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path


class AppointmentEngine:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.doctors_path = self.data_dir / "doctors.json"
        self.appointments_path = self.data_dir / "appointments.json"
        self._ensure_seed_data()

    def _ensure_seed_data(self) -> None:
        if not self.doctors_path.exists():
            doctors = [
                {
                    "doctor_id": "doc-001",
                    "doctor_name": "Dr Sharma",
                    "specialty": "cardiologist",
                    "hospital": "Apollo",
                    "availability": {
                        "today": ["10 am", "11 am", "2 pm"],
                        "tomorrow": ["10 am", "2 pm", "4 pm"],
                        "friday": ["10:30 am", "2:00 pm", "4:30 pm"],
                    },
                },
                {
                    "doctor_id": "doc-002",
                    "doctor_name": "Dr Meena",
                    "specialty": "dermatologist",
                    "hospital": "Apollo",
                    "availability": {
                        "today": ["12 pm", "2 pm"],
                        "tomorrow": ["11 am", "4 pm"],
                        "friday": ["10 am", "12 pm"],
                    },
                },
                {
                    "doctor_id": "doc-003",
                    "doctor_name": "Dr Arul",
                    "specialty": "pediatrician",
                    "hospital": "City Care",
                    "availability": {
                        "today": ["10 am", "1 pm"],
                        "tomorrow": ["9 am", "11 am", "3 pm"],
                        "friday": ["11 am", "2 pm"],
                    },
                },
            ]
            self.doctors_path.write_text(json.dumps(doctors, indent=2), encoding="utf-8")
        if not self.appointments_path.exists():
            self.appointments_path.write_text("[]", encoding="utf-8")

    def _read_doctors(self) -> list[dict]:
        return json.loads(self.doctors_path.read_text(encoding="utf-8"))

    def _read_appointments(self) -> list[dict]:
        return json.loads(self.appointments_path.read_text(encoding="utf-8"))

    def _write_appointments(self, appointments: list[dict]) -> None:
        self.appointments_path.write_text(json.dumps(appointments, indent=2), encoding="utf-8")

    def check_availability(self, specialty: str | None, date: str | None) -> dict:
        doctors = self._read_doctors()
        if not specialty or not date:
            return {"message": "Please provide both specialty and date to check availability.", "suggestions": []}
        matches = [doctor for doctor in doctors if doctor["specialty"] == specialty]
        if not matches:
            return {"message": f"No {specialty} found in the network.", "suggestions": []}
        suggestions: list[str] = []
        for doctor in matches:
            slots = doctor["availability"].get(date, [])
            booked_slots = {
                item["time"]
                for item in self._read_appointments()
                if item["doctor_id"] == doctor["doctor_id"] and item["date"] == date and item["status"] != "cancelled"
            }
            open_slots = [slot for slot in slots if slot not in booked_slots]
            suggestions.extend([f'{doctor["doctor_name"]} at {slot}' for slot in open_slots])
        if not suggestions:
            return {"message": f"No open slots found for {specialty} on {date}.", "suggestions": []}
        return {"message": f"Available slots for {specialty} on {date}: {', '.join(suggestions)}.", "suggestions": suggestions}

    def book_appointment(self, patient_id: str, specialty: str | None, doctor_name: str | None, date: str | None, time: str | None) -> dict:
        if not specialty or not date or not time:
            return {"message": "Doctor specialty, date, and time are required for booking.", "suggestions": []}
        if self._is_past_time(date, time):
            return {"message": "Appointments cannot be booked in the past.", "suggestions": []}
        doctors = self._read_doctors()
        candidates = [doctor for doctor in doctors if doctor["specialty"] == specialty]
        if doctor_name:
            candidates = [doctor for doctor in candidates if doctor["doctor_name"].lower() == doctor_name.lower()]
        if not candidates:
            return {"message": f"No doctor found for {specialty}.", "suggestions": []}
        appointments = self._read_appointments()
        for doctor in candidates:
            available_slots = doctor["availability"].get(date, [])
            if time not in available_slots:
                continue
            conflict = any(
                item["doctor_id"] == doctor["doctor_id"] and item["date"] == date and item["time"] == time and item["status"] != "cancelled"
                for item in appointments
            )
            if conflict:
                alternatives = self._suggest_alternatives(doctor["doctor_id"], date, available_slots, appointments)
                return {"message": f"That slot is already booked. Alternatives are: {', '.join(alternatives)}.", "suggestions": alternatives}
            appointment = {
                "id": f"apt-{uuid.uuid4().hex[:8]}",
                "patient_id": patient_id,
                "doctor_id": doctor["doctor_id"],
                "doctor_name": doctor["doctor_name"],
                "specialty": doctor["specialty"],
                "hospital": doctor["hospital"],
                "date": date,
                "time": time,
                "status": "booked",
                "created_at": datetime.now(UTC).isoformat(),
            }
            appointments.append(appointment)
            self._write_appointments(appointments)
            return {"message": f"Your appointment with {doctor['doctor_name']} is booked for {date} at {time}.", "appointment": appointment, "suggestions": []}
        return {"message": f"{specialty} is unavailable at {time} on {date}.", "suggestions": []}

    def cancel_appointment(self, patient_id: str, appointment_id: str | None) -> dict:
        if not appointment_id:
            appointment_id = self._find_latest_appointment_id(patient_id)
        appointments = self._read_appointments()
        for appointment in appointments:
            if appointment["id"] == appointment_id and appointment["patient_id"] == patient_id and appointment["status"] != "cancelled":
                appointment["status"] = "cancelled"
                self._write_appointments(appointments)
                return {"message": f"Appointment {appointment['id']} has been cancelled.", "appointment": appointment, "suggestions": []}
        return {"message": "I could not find an active appointment to cancel.", "suggestions": []}

    def reschedule_appointment(self, patient_id: str, appointment_id: str | None, new_date: str | None, new_time: str | None) -> dict:
        if not appointment_id:
            appointment_id = self._find_latest_appointment_id(patient_id)
        if not new_date or not new_time:
            return {"message": "New date and time are required for rescheduling.", "suggestions": []}
        if self._is_past_time(new_date, new_time):
            return {"message": "Appointments cannot be moved to a past time.", "suggestions": []}
        appointments = self._read_appointments()
        target = next(
            (
                appointment
                for appointment in appointments
                if appointment["id"] == appointment_id and appointment["patient_id"] == patient_id and appointment["status"] != "cancelled"
            ),
            None,
        )
        if not target:
            return {"message": "I could not find an active appointment to reschedule.", "suggestions": []}
        doctor = next((doctor for doctor in self._read_doctors() if doctor["doctor_id"] == target["doctor_id"]), None)
        if not doctor:
            return {"message": "Doctor schedule could not be loaded.", "suggestions": []}
        available_slots = doctor["availability"].get(new_date, [])
        if new_time not in available_slots:
            return {"message": f"{doctor['doctor_name']} is not available at {new_time} on {new_date}.", "suggestions": available_slots}
        conflict = any(
            appointment["doctor_id"] == target["doctor_id"]
            and appointment["date"] == new_date
            and appointment["time"] == new_time
            and appointment["status"] != "cancelled"
            and appointment["id"] != target["id"]
            for appointment in appointments
        )
        if conflict:
            alternatives = self._suggest_alternatives(target["doctor_id"], new_date, available_slots, appointments)
            return {"message": f"That slot is already taken. Alternatives are: {', '.join(alternatives)}.", "suggestions": alternatives}
        target["date"] = new_date
        target["time"] = new_time
        target["status"] = "rescheduled"
        self._write_appointments(appointments)
        return {"message": f"Your appointment has been moved to {new_date} at {new_time}.", "appointment": target, "suggestions": []}

    def _find_latest_appointment_id(self, patient_id: str) -> str | None:
        appointments = [item for item in self._read_appointments() if item["patient_id"] == patient_id and item["status"] != "cancelled"]
        if not appointments:
            return None
        appointments.sort(key=lambda item: item["created_at"], reverse=True)
        return appointments[0]["id"]

    @staticmethod
    def _suggest_alternatives(doctor_id: str, date: str, available_slots: list[str], appointments: list[dict]) -> list[str]:
        booked_slots = {
            item["time"]
            for item in appointments
            if item["doctor_id"] == doctor_id and item["date"] == date and item["status"] != "cancelled"
        }
        return [slot for slot in available_slots if slot not in booked_slots][:3]

    @staticmethod
    def _is_past_time(date_label: str, time_label: str) -> bool:
        if date_label != "today":
            return False
        time_map = {
            "9 am": 9,
            "10 am": 10,
            "10:30 am": 10.5,
            "11 am": 11,
            "12 pm": 12,
            "1 pm": 13,
            "2 pm": 14,
            "2:00 pm": 14,
            "3 pm": 15,
            "4 pm": 16,
            "4:30 pm": 16.5,
        }
        current_hour = datetime.now().hour + (0.5 if datetime.now().minute >= 30 else 0.0)
        slot_hour = time_map.get(time_label.lower())
        return slot_hour is not None and slot_hour < current_hour
