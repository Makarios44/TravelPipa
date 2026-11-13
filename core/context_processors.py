from urllib.parse import quote

from django.conf import settings
from django.utils.translation import get_language, gettext as _

from .i18n import current_suffix
from .models import SiteSettings
from .seo import absolute_url, language_alternates

LANGUAGE_SHORT = {"en": "EN", "pt-br": "PT", "es": "ES"}


def whatsapp_link(site, message=""):
    if not site.whatsapp_digits:
        return ""
    url = f"https://wa.me/{site.whatsapp_digits}"
    if message:
        url += "?text=" + quote(message)
    return url


def site_context(request):
    # The admin does not need any of this.
    if request.path.startswith("/" + settings.ADMIN_URL):
        return {}
    site = SiteSettings.load()
    lang = get_language() or settings.LANGUAGE_CODE
    alternates = language_alternates(request)
    languages = [
        {
            "code": code,
            "name": name,
            "short": LANGUAGE_SHORT.get(code, code.upper()),
            "path": path,
            "url": absolute_url(request, path),
            "current": code == lang,
        }
        for (code, name), (_code, path) in zip(settings.LANGUAGES, alternates)
    ]
    default_path = next(p for c, p in alternates if c == settings.LANGUAGE_CODE)
    return {
        "site": site,
        "lang_suffix": current_suffix(lang),
        "site_languages": languages,
        "canonical_url": absolute_url(request, request.path),
        "x_default_url": absolute_url(request, default_path),
        "whatsapp_general_url": whatsapp_link(site, _("Hello! I'd like some information about TravelPipa experiences.")),
        "og_locale": {"en": "en_US", "pt-br": "pt_BR", "es": "es_ES"}.get(lang, "en_US"),
    }
