"""
Helpers for multilingual model content.

Every translatable field is stored as three columns with a language suffix:
``title_en``, ``title_pt``, ``title_es``. The ``Localized`` descriptor exposes
``obj.title`` and returns the value for the active language, falling back to
English when the translation is empty.
"""
from django.utils.translation import get_language

# Django language code -> model field suffix
LANG_SUFFIX = {"en": "en", "pt-br": "pt", "es": "es"}
SUFFIXES = ("en", "pt", "es")
SUFFIX_LABELS = {"en": "Inglês", "pt": "Português", "es": "Espanhol"}
DEFAULT_SUFFIX = "en"


def current_suffix(language=None):
    code = (language or get_language() or "en").lower()
    if code in LANG_SUFFIX:
        return LANG_SUFFIX[code]
    return LANG_SUFFIX.get(code.split("-")[0], DEFAULT_SUFFIX)


def localized_value(obj, base, language=None, fallback=True):
    value = getattr(obj, f"{base}_{current_suffix(language)}", "") or ""
    if not value and fallback:
        value = getattr(obj, f"{base}_{DEFAULT_SUFFIX}", "") or ""
    return value


class Localized:
    """Descriptor: ``title = Localized()`` reads ``title_<lang>`` with English fallback."""

    def __init__(self, fallback=True):
        self.fallback = fallback

    def __set_name__(self, owner, name):
        self.base = name

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        return localized_value(obj, self.base, fallback=self.fallback)


def lines(text):
    """Split a multi-line text field into a clean list (one item per line)."""
    return [line.strip(" -•\t") for line in (text or "").splitlines() if line.strip(" -•\t")]


def localized_fields(*bases):
    """List of concrete field names for the given bases, e.g. title_en, title_pt..."""
    return [f"{base}_{suffix}" for base in bases for suffix in SUFFIXES]
