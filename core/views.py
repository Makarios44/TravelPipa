from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, translate_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import get_language, get_language_from_path, gettext as _, override
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from bookings.notifications import notify_new_contact
from tours.models import Category, Experience

from .antispam import rate_limited
from .conditions import get_conditions
from .forms import ContactForm
from .i18n import current_suffix
from .models import SiteSettings, Testimonial
from .seo import agency_schema, json_ld


def home(request):
    site = SiteSettings.load()
    tours = Experience.objects.tours()
    featured = list(tours.filter(featured=True)[:6]) or list(tours[:6])
    transfers = list(Experience.objects.transfers().order_by("-featured", "order")[:3])
    testimonials = list(Testimonial.objects.for_language(current_suffix())[:6])
    categories = Category.objects.active().filter(is_transfer=False)
    rest = len(featured) - 1
    rest_col = "col-md-6" if rest in (2, 4) else "col-md-6 col-lg-4"
    return render(request, "core/home.html", {
        "featured": featured,
        "rest_col": rest_col,
        "transfers": transfers,
        "main_transfer": transfers[0] if transfers else None,
        "testimonials": testimonials,
        "categories": categories,
        "schema": json_ld(agency_schema(request, site)),
    })


def about(request):
    return render(request, "core/about.html")


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if rate_limited(request, "contact"):
            form.add_error(None, _("Too many messages from this connection. Please try again later or use WhatsApp."))
        elif form.is_valid():
            message = form.save(language=get_language())
            notify_new_contact(request, message)
            messages.success(request, _("Thank you! Your message was sent. We will reply as soon as possible."))
            return redirect("core:contact")
    else:
        form = ContactForm()
    return render(request, "core/contact.html", {"form": form})


def privacy(request):
    return render(request, "core/legal.html", {"page": "privacy"})


def terms(request):
    return render(request, "core/legal.html", {"page": "terms"})


@require_GET
def switch_language(request, lang_code):
    """Switch language, remember the choice in a cookie and go to the same page translated."""
    available = dict(settings.LANGUAGES)
    if lang_code not in available:
        lang_code = settings.LANGUAGE_CODE
    next_url = request.GET.get("next", "/")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
        next_url = "/"
    # translate_url resolves the path in the active language, so use the language of ``next``.
    source_lang = get_language_from_path(next_url.split("?")[0]) or settings.LANGUAGE_CODE
    with override(source_lang):
        target = translate_url(next_url, lang_code)
    if target == next_url and not next_url.startswith(f"/{lang_code}/"):
        with override(lang_code):
            target = reverse("core:home")
    response = HttpResponseRedirect(target)
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME, lang_code,
        max_age=settings.LANGUAGE_COOKIE_AGE, samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        secure=getattr(settings, "LANGUAGE_COOKIE_SECURE", False), httponly=False,
    )
    return response


@require_GET
@cache_control(max_age=60 * 60 * 24)
def robots_txt(request):
    sitemap_url = (settings.SITE_URL or request.build_absolute_uri("/").rstrip("/")) + "/sitemap.xml"
    lines = [
        "User-agent: *",
        "Disallow: /*/book/thanks/",
        "Disallow: /*/reservar/obrigado/",
        "Disallow: /*/reservar/gracias/",
        "Disallow: /i18n/",
        "Disallow: /*/widgets/",
        "Allow: /",
        "",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def tides_weather(request):
    """Tides & weather page (server-rendered: good for SEO searches like 'tábua de marés Pipa')."""
    tide_tours = Experience.objects.published().filter(tide_dependent=True)
    return render(request, "core/tides_weather.html", {"conditions": get_conditions(), "tide_tours": tide_tours})


def conditions_widget(request):
    """Small HTML fragment loaded asynchronously, so external APIs never slow a page down."""
    variant = request.GET.get("v", "compact")
    template = "includes/conditions_tide_box.html" if variant == "tide" else "includes/conditions_compact.html"
    response = render(request, template, {"conditions": get_conditions()})
    response["Cache-Control"] = "public, max-age=600"
    response["X-Robots-Tag"] = "noindex"
    return response
