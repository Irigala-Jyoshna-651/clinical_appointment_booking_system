class Localizer:
    def __init__(self):
        self.prefixes = {
            "en": "",
            "hi": "\u0939\u093f\u0902\u0926\u0940 \u0938\u0939\u093e\u092f\u0924\u093e: ",
            "ta": "\u0ba4\u0bae\u0bbf\u0bb4\u0bcd \u0b89\u0ba4\u0bb5\u0bbf: ",
            "te": "\u0c24\u0c46\u0c32\u0c41\u0c17\u0c41 \u0c38\u0c39\u0c3e\u0c2f\u0c02: ",
            "kn": "\u0c95\u0ca8\u0ccd\u0ca8\u0ca1 \u0cb8\u0cb9\u0cbe\u0caf: ",
        }

    def render(self, language: str, base_text: str, patient_profile: dict, action: str, suggestions: list[str]) -> str:
        preferred_hospital = patient_profile.get("preferred_hospital")
        if action in {"book", "reschedule", "cancel"} and preferred_hospital and preferred_hospital not in base_text:
            base_text = f"{base_text} Preferred hospital on file: {preferred_hospital}."
        if suggestions:
            base_text = f"{base_text} Suggested options: {', '.join(suggestions)}."
        return f"{self.prefixes.get(language, '')}{base_text}"
