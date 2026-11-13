from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.utils import translation


class AdminLanguageMiddleware:
    """Always show the admin and the management panel in Portuguese for the local team."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.prefixes = ("/" + settings.ADMIN_URL, "/" + settings.PANEL_URL)

    def __call__(self, request):
        if request.path.startswith(self.prefixes):
            translation.activate(settings.ADMIN_LANGUAGE)
            request.LANGUAGE_CODE = settings.ADMIN_LANGUAGE
        return self.get_response(request)


class CanonicalHostMiddleware:
    """
    301-redirect every request on another host (www., *.up.railway.app) to the
    canonical domain from SITE_URL, so Google indexes a single address.
    The health check stays reachable on any host.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.host = getattr(settings, "CANONICAL_HOST", "")

    def __call__(self, request):
        if self.host and not settings.DEBUG and request.path != "/healthz/":
            if request.get_host().lower() != self.host:
                return HttpResponsePermanentRedirect(f"https://{self.host}{request.get_full_path()}")
        return self.get_response(request)


# Everything (CSS, JS, fonts, images, video) is served by the site itself, so the
# browser can be told to refuse anything injected from elsewhere.
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "media-src 'self' blob:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"


class SecurityHeadersMiddleware:
    """Content-Security-Policy and Permissions-Policy on every HTML response."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_prefix = "/" + settings.ADMIN_URL

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        content_type = response.get("Content-Type", "")
        # Django's technical admin ships a few inline scripts, so it keeps the default policy.
        if content_type.startswith("text/html") and not request.path.startswith(self.admin_prefix):
            response.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        return response
