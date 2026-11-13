from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from tours.models import Experience


class I18nSitemap(Sitemap):
    """Every URL is listed once per language, with hreflang alternates."""

    i18n = True
    alternates = True
    x_default = True
    languages = [code for code, _ in settings.LANGUAGES]

    def get_domain(self, site=None):
        if settings.SITE_URL:
            return settings.SITE_URL.split("://", 1)[-1]
        return super().get_domain(site)

    def get_protocol(self, protocol=None):
        if settings.SITE_URL.startswith("https://"):
            return "https"
        return super().get_protocol(protocol)


class StaticPagesSitemap(I18nSitemap):
    def changefreq(self, item):
        return "daily" if item == "core:tides_weather" else "monthly"

    def items(self):
        return ["core:home", "tours:experience_list", "tours:transfers", "core:about", "core:contact",
                "bookings:request", "core:tides_weather", "core:privacy", "core:terms"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return {"core:home": 1.0, "tours:experience_list": 0.9, "tours:transfers": 0.8, "core:tides_weather": 0.7}.get(item, 0.5)


class ExperienceSitemap(I18nSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Experience.objects.published().order_by("pk")

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {"pages": StaticPagesSitemap, "experiences": ExperienceSitemap}
