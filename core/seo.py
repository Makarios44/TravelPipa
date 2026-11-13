"""SEO helpers: absolute URLs, hreflang alternates and JSON-LD structured data."""
import json

from django.conf import settings
from django.urls import translate_url
from django.utils.html import escape
from django.utils.safestring import mark_safe


def absolute_url(request, path):
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if settings.SITE_URL:
        return settings.SITE_URL + path
    return request.build_absolute_uri(path)


def language_alternates(request):
    """[(lang_code, path)] for the current page in every language."""
    path = request.path
    alternates = []
    for code, _name in settings.LANGUAGES:
        alternates.append((code, translate_url(path, code)))
    return alternates


def json_ld(data):
    """Render a dict as a safe <script type="application/ld+json"> block."""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    # Prevent closing the script tag from inside the JSON.
    payload = payload.replace("</", "<\\/")
    return mark_safe(f'<script type="application/ld+json">{payload}</script>')


def agency_schema(request, site):
    """TravelAgency data built only from information filled in the admin."""
    data = {
        "@context": "https://schema.org",
        "@type": "TravelAgency",
        "name": site.site_name,
        "url": absolute_url(request, "/"),
        "areaServed": {"@type": "Place", "name": "Praia da Pipa, Rio Grande do Norte, Brazil"},
    }
    if site.logo:
        data["logo"] = absolute_url(request, site.logo.url)
    if site.hero_image:
        data["image"] = absolute_url(request, site.hero_image.url)
    if site.email:
        data["email"] = site.email
    if site.phone or site.whatsapp:
        data["telephone"] = site.phone or site.whatsapp
    if site.address:
        data["address"] = {"@type": "PostalAddress", "streetAddress": site.address,
                           "addressCountry": "BR"}
    same_as = [link["url"] for link in site.social_links]
    if same_as:
        data["sameAs"] = same_as
    return data


def experience_schema(request, experience, site):
    """TouristTrip data. Offers are only added when a real price is filled in."""
    data = {
        "@context": "https://schema.org",
        "@type": "TouristTrip",
        "name": experience.title,
        "description": experience.meta_description or experience.summary or experience.title,
        "url": absolute_url(request, experience.get_absolute_url()),
        "touristType": "International and domestic travellers",
        "provider": {"@type": "TravelAgency", "name": site.site_name, "url": absolute_url(request, "/")},
    }
    images = [absolute_url(request, img.image.url) for img in experience.gallery]
    if images:
        data["image"] = images
    if experience.itinerary_list:
        data["itinerary"] = {
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i, "name": step}
                for i, step in enumerate(experience.itinerary_list, start=1)
            ],
        }
    if experience.price is not None and not experience.is_demo:
        data["offers"] = {
            "@type": "Offer",
            "price": str(experience.price),
            "priceCurrency": experience.currency,
            "url": data["url"],
        }
    return data


def breadcrumb_schema(request, items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": str(name), "item": absolute_url(request, url)}
            for i, (name, url) in enumerate(items, start=1)
        ],
    }


def meta_escape(value):
    return escape(" ".join(str(value or "").split()))
