from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import redis


class PersistentMemoryStore:
    def __init__(self, redis_url: str, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.patients_path = self.data_dir / "patients.json"
        self.interactions_path = self.data_dir / "interactions.json"
        self._redis = None
        try:
            self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
        except Exception:
            self._redis = None
        self._ensure_files()

    def _ensure_files(self) -> None:
        if not self.patients_path.exists():
            self.patients_path.write_text("{}", encoding="utf-8")
        if not self.interactions_path.exists():
            self.interactions_path.write_text("{}", encoding="utf-8")

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_patient_profile(self, patient_id: str) -> dict[str, Any]:
        if self._redis:
            raw = self._redis.get(f"patient:{patient_id}")
            if raw:
                return json.loads(raw)
        patients = self._read_json(self.patients_path)
        return patients.get(
            patient_id,
            {
                "patient_id": patient_id,
                "preferred_language": "en",
                "preferred_hospital": "Apollo",
                "last_appointment": None,
                "past_appointments": [],
            },
        )

    def save_patient_profile(self, patient_id: str, profile: dict[str, Any]) -> None:
        patients = self._read_json(self.patients_path)
        patients[patient_id] = profile
        self._write_json(self.patients_path, patients)
        if self._redis:
            self._redis.set(f"patient:{patient_id}", json.dumps(profile))

    def record_appointment(self, patient_id: str, appointment: dict[str, Any]) -> None:
        profile = self.get_patient_profile(patient_id)
        profile["last_appointment"] = appointment
        profile.setdefault("past_appointments", []).append(appointment)
        self.save_patient_profile(patient_id, profile)

    def record_interaction(self, patient_id: str, interaction: dict[str, Any]) -> None:
        interactions = self._read_json(self.interactions_path)
        patient_interactions = interactions.setdefault(patient_id, [])
        patient_interactions.append(interaction)
        self._write_json(self.interactions_path, interactions)
