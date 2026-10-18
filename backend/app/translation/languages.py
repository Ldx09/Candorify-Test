"""Languages users can pick. English is the official language: letters are always generated and sent
in English, and translations are read-only copies. Add a language by adding one line here."""
from pydantic import BaseModel


class Language(BaseModel):
    code: str     # ISO 639-1 code (or with region, e.g. zh-TW)
    name: str     # English name
    native: str   # name in the language itself, for the dropdown
    rtl: bool = False  # right-to-left script: the frontend should set dir="rtl"


LANGUAGES: list[Language] = [Language(code=c, name=n, native=nat, rtl=r) for c, n, nat, r in [
    ("en", "English", "English", False),
    ("es", "Spanish", "Español", False),
    ("zh", "Chinese (Simplified)", "简体中文", False),
    ("zh-TW", "Chinese (Traditional)", "繁體中文", False),
    ("tl", "Tagalog", "Tagalog", False),
    ("vi", "Vietnamese", "Tiếng Việt", False),
    ("ar", "Arabic", "العربية", True),
    ("fr", "French", "Français", False),
    ("ko", "Korean", "한국어", False),
    ("ru", "Russian", "Русский", False),
    ("pt", "Portuguese", "Português", False),
    ("ht", "Haitian Creole", "Kreyòl ayisyen", False),
    ("hi", "Hindi", "हिन्दी", False),
    ("de", "German", "Deutsch", False),
    ("pl", "Polish", "Polski", False),
    ("it", "Italian", "Italiano", False),
    ("ur", "Urdu", "اردو", True),
    ("fa", "Persian (Farsi)", "فارسی", True),
    ("bn", "Bengali", "বাংলা", False),
    ("gu", "Gujarati", "ગુજરાતી", False),
    ("pa", "Punjabi", "ਪੰਜਾਬੀ", False),
    ("te", "Telugu", "తెలుగు", False),
    ("ta", "Tamil", "தமிழ்", False),
    ("ja", "Japanese", "日本語", False),
    ("he", "Hebrew", "עברית", True),
    ("el", "Greek", "Ελληνικά", False),
    ("uk", "Ukrainian", "Українська", False),
    ("am", "Amharic", "አማርኛ", False),
    ("so", "Somali", "Soomaali", False),
    ("sw", "Swahili", "Kiswahili", False),
    ("yo", "Yoruba", "Yorùbá", False),
    ("ne", "Nepali", "नेपाली", False),
    ("km", "Khmer", "ខ្មែរ", False),
    ("hmn", "Hmong", "Hmoob", False),
    ]]

BY_CODE: dict[str, Language] = {lang.code.lower(): lang for lang in LANGUAGES}


def get_language(code: str) -> Language | None:
    return BY_CODE.get(code.strip().lower())