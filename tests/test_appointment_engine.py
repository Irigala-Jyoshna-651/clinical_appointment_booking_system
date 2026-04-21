from pathlib import Path

from scheduler.appointment_engine import AppointmentEngine


def test_booking_and_conflict_flow(tmp_path: Path):
    engine = AppointmentEngine(data_dir=tmp_path)
    booking = engine.book_appointment("pat-1", "cardiologist", None, "tomorrow", "10 am")
    assert booking["appointment"]["status"] == "booked"

    conflict = engine.book_appointment("pat-2", "cardiologist", None, "tomorrow", "10 am")
    assert "already booked" in conflict["message"]
    assert conflict["suggestions"]


def test_reschedule_and_cancel_flow(tmp_path: Path):
    engine = AppointmentEngine(data_dir=tmp_path)
    booking = engine.book_appointment("pat-1", "dermatologist", None, "tomorrow", "11 am")
    appointment_id = booking["appointment"]["id"]

    moved = engine.reschedule_appointment("pat-1", appointment_id, "friday", "10 am")
    assert moved["appointment"]["status"] == "rescheduled"

    cancelled = engine.cancel_appointment("pat-1", appointment_id)
    assert cancelled["appointment"]["status"] == "cancelled"
