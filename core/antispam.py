"""
Lightweight spam protection for public forms, without third-party services:

* a hidden "honeypot" field that real visitors never fill in;
* a signed timestamp that rejects forms submitted faster than a human could;
* a per-IP rate limit (hashed IP, nothing personal is stored).
"""
import hashlib
import time

from django import forms
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

SIGNER_SALT = "travelpipa.form-timestamp"


class AntiSpamFormMixin(forms.Form):
    website = forms.CharField(required=False, label="Website", widget=forms.TextInput(
        attrs={"autocomplete": "off", "tabindex": "-1"}))
    form_ts = forms.CharField(required=False, widget=forms.HiddenInput)

    spam_error = _("We could not process your submission. Please wait a few seconds and try again.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["form_ts"] = signing.dumps(time.time(), salt=SIGNER_SALT)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError(self.spam_error, code="spam")
        try:
            started = signing.loads(cleaned.get("form_ts") or "", salt=SIGNER_SALT, max_age=60 * 60 * 6)
        except signing.BadSignature:
            raise forms.ValidationError(self.spam_error, code="spam")
        if time.time() - float(started) < settings.FORM_MIN_FILL_SECONDS:
            raise forms.ValidationError(self.spam_error, code="spam")
        return cleaned


def client_ip(request):
    """
    The visitor's IP. Each trusted proxy (Railway, optionally Cloudflare) appends
    the address it received the connection from to X-Forwarded-For, so the real
    IP is the N-th entry from the right. Entries further left are written by the
    visitor and could be forged to escape the rate limits.
    """
    forwarded = [part.strip() for part in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if part.strip()]
    proxies = max(getattr(settings, "TRUSTED_PROXY_COUNT", 1), 0)
    if proxies and forwarded:
        return forwarded[-min(proxies, len(forwarded))]
    return request.META.get("REMOTE_ADDR", "")


def client_ip_hash(request):
    ip = client_ip(request)
    return hashlib.sha256(f"{settings.SECRET_KEY}:{ip}".encode()).hexdigest()[:32]


def rate_limited(request, scope):
    """True when this visitor exceeded the hourly limit for ``scope``. Counts the attempt."""
    limit = settings.FORM_RATE_LIMIT_PER_HOUR
    if limit <= 0:
        return False
    key = f"rl:{scope}:{client_ip_hash(request)}"
    added = cache.add(key, 1, 60 * 60)
    if added:
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, 60 * 60)
        return False
    return count > limit
