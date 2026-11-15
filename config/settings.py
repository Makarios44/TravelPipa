"""
Django settings for the TravelPipa project.

All sensitive or environment-specific values come from environment variables
(see .env.example). Nothing secret is hard-coded here.
"""
import os
from pathlib import Path
from urllib.parse import urlsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
DEBUG = env_bool("DEBUG", True)

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured("SECRET_KEY environment variable is required when DEBUG is off.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Public base URL used for canonical links, sitemap and Open Graph (no trailing slash).
# Production: https://travelpipa.com.br
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
# Every other host (www., the *.up.railway.app address) is redirected (301) to this one.
CANONICAL_HOST = urlsplit(SITE_URL).netloc.lower() if SITE_URL.startswith("https://") else ""
if CANONICAL_HOST:
    for _host in (CANONICAL_HOST, "www." + CANONICAL_HOST.removeprefix("www.")):
        if _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)
        if f"https://{_host}" not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(f"https://{_host}")

# Host used by Railway's health checks.
ALLOWED_HOSTS.append("healthcheck.railway.app")

# Railway exposes the public domain in this variable.
_railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
if _railway_domain:
    ALLOWED_HOSTS.append(_railway_domain)
    CSRF_TRUSTED_ORIGINS.append(f"https://{_railway_domain}")

# Google reviews shown on the site (Places API key, restricted to the Places API).
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")

# Test/staging copy of the site (branch "model"): hidden from search engines,
# with a visible banner, so it never competes with travelpipa.com.br.
STAGING = env_bool("STAGING", False)

# Number of reverse proxies in front of the app that append to X-Forwarded-For
# (Railway = 1; Railway behind Cloudflare's orange cloud = 2). Used to find the
# visitor's real IP for rate limiting without trusting values the visitor can forge.
TRUSTED_PROXY_COUNT = int(os.environ.get("TRUSTED_PROXY_COUNT", "1"))

# The admin lives on a configurable path so it is not at the obvious /admin/.
ADMIN_URL = os.environ.get("ADMIN_URL", "painel/").strip("/") + "/"
# TravelPipa management panel (the team's day-to-day area)
PANEL_URL = os.environ.get("PANEL_URL", "gestao/").strip("/") + "/"
LOGIN_URL = "panel:login"
# Panel login protection: attempts allowed per user+IP within the window
PANEL_LOGIN_MAX_ATTEMPTS = int(os.environ.get("PANEL_LOGIN_MAX_ATTEMPTS", "5"))
PANEL_LOGIN_LOCK_MINUTES = int(os.environ.get("PANEL_LOGIN_LOCK_MINUTES", "15"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    # Project apps
    "core.apps.CoreConfig",
    "tours.apps.ToursConfig",
    "bookings.apps.BookingsConfig",
    "panel.apps.PanelConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.CanonicalHostMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "core.middleware.AdminLanguageMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "core.context_processors.site_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --------------------------------------------------------------------------
# Database: PostgreSQL in production (DATABASE_URL), SQLite for development.
# --------------------------------------------------------------------------
if not DEBUG and not os.environ.get("DATABASE_URL") and not env_bool("ALLOW_SQLITE_IN_PRODUCTION", False):
    # On Railway the container disk is erased on every deploy: an SQLite file there
    # would silently lose bookings, users and photos. Fail loudly instead.
    raise ImproperlyConfigured(
        "DATABASE_URL is not set. On Railway use DATABASE_URL=${{Postgres.DATABASE_URL}}.")

DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------
# Internationalisation
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("pt-br", "Português"),
    ("es", "Español"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_NAME = "travelpipa_lang"
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365
LANGUAGE_COOKIE_SAMESITE = "Lax"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True

# Language used inside the admin panel (operated by the local team).
ADMIN_LANGUAGE = "pt-br"

# --------------------------------------------------------------------------
# Static and media files
# --------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT") or BASE_DIR / "media")
# Serve uploaded media through Django (useful on Railway with a mounted volume).
SERVE_MEDIA = env_bool("SERVE_MEDIA", DEBUG) if os.environ.get("SERVE_MEDIA") else DEBUG

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

# Uploaded images larger than this are resized on save (pixels, longest side).
IMAGE_MAX_SIDE = 2560
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # larger uploads go to a temp file
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# --------------------------------------------------------------------------
# E-mail
# Railway blocks SMTP on Free/Trial/Hobby plans, so production uses the Resend
# HTTPS API (RESEND_API_KEY). SMTP (EMAIL_HOST) still works on other hosts.
# Without either, e-mails are only printed to the log and requests are still saved.
# --------------------------------------------------------------------------
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "TravelPipa <suporte@travelpipa.com.br>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_SUBJECT_PREFIX = "[TravelPipa] "
# Comma separated list; falls back to the e-mail set in the panel (Configurações).
NOTIFICATION_EMAILS = env_list("NOTIFICATION_EMAILS")
if RESEND_API_KEY:
    EMAIL_BACKEND = "core.email_backends.ResendEmailBackend"
elif EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_ENABLED = bool(RESEND_API_KEY or EMAIL_HOST)
# Who receives an e-mail when the site has an error (500). Comma separated.
ADMINS = [("TravelPipa", addr) for addr in env_list("ERROR_EMAILS")]

# --------------------------------------------------------------------------
# Cache (used for form rate limiting)
# --------------------------------------------------------------------------
# Database cache: shared by every Gunicorn worker and kept across restarts/deploys.
# The table is created by a migration (core 0002), so no extra command is needed.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "travelpipa_cache"}}

# Anti-spam: max form submissions per IP per hour, and min seconds to fill a form.
FORM_RATE_LIMIT_PER_HOUR = int(os.environ.get("FORM_RATE_LIMIT_PER_HOUR", "8"))
FORM_MIN_FILL_SECONDS = int(os.environ.get("FORM_MIN_FILL_SECONDS", "3"))

# --------------------------------------------------------------------------
# Security
# --------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24 * 3  # panel logins expire after 3 days
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    LANGUAGE_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "2592000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_HSTS_PRELOAD = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}

# --------------------------------------------------------------------------
# Tides & weather ("Tides & Weather" page and widgets)
# --------------------------------------------------------------------------
# Centre of Praia da Pipa
CONDITIONS_LAT = float(os.environ.get("CONDITIONS_LAT", "-6.2283"))
CONDITIONS_LON = float(os.environ.get("CONDITIONS_LON", "-35.0464"))
# Weather from MET Norway (free, commercial use allowed). Their terms require an
# identifying User-Agent with a way to contact the site owner.
WEATHER_ENABLED = env_bool("WEATHER_ENABLED", True)
WEATHER_CONTACT = os.environ.get("WEATHER_CONTACT", "")
WEATHER_USER_AGENT = "TravelPipa/1.0 " + (
    f"({SITE_URL}{' ' + WEATHER_CONTACT if WEATHER_CONTACT else ''})" if SITE_URL or WEATHER_CONTACT else "(travelpipa)"
)
# Tides. "tabuamare" (default, free): Brazilian Navy predictions via tabuamare.api.br.
# "worldtides": paid alternative (needs WORLDTIDES_API_KEY).
TIDES_PROVIDER = os.environ.get("TIDES_PROVIDER", "tabuamare").strip().lower()
TIDES_STATE = os.environ.get("TIDES_STATE", "rn").strip().lower()  # state used to find the nearest port
TABUAMARE_API_KEY = os.environ.get("TABUAMARE_API_KEY", "")  # optional free key: own quota, not shared per IP
WORLDTIDES_API_KEY = os.environ.get("WORLDTIDES_API_KEY", "")
