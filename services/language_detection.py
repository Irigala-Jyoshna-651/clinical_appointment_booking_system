class LanguageDetector:
    def detect(self, text: str, fallback: str = "en") -> str:
        if any("\u0900" <= char <= "\u097f" for char in text):
            return "hi"
        if any("\u0b80" <= char <= "\u0bff" for char in text):
            return "ta"
        if any("\u0c00" <= char <= "\u0c7f" for char in text):
            return "te"
        if any("\u0c80" <= char <= "\u0cff" for char in text):
            return "kn"
        hindi_tokens = ["namaste", "kal", "doctor se", "appointment"]
        tamil_tokens = ["vanakkam", "naalai", "maruththuv", "parka"]
        telugu_tokens = ["namaskaram", "repu", "doctor", "appointment", "book cheyyi"]
        kannada_tokens = ["namaskara", "naale", "vaidya", "appointment", "book madi"]
        lowered = text.lower()
        if any(token in lowered for token in hindi_tokens):
            return "hi"
        if any(token in lowered for token in tamil_tokens):
            return "ta"
        if any(token in lowered for token in telugu_tokens):
            return "te"
        if any(token in lowered for token in kannada_tokens):
            return "kn"
        return fallback if fallback in {"en", "hi", "ta", "te", "kn"} else "en"
