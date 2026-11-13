"""URL configuration. Public pages are prefixed by language: /en/, /pt-br/, /es/."""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from core import views as core_views
from core.media_views import serve_media
from core.sitemaps import SITEMAPS

admin.site.site_header = "TravelPipa — Painel"
admin.site.site_title = "TravelPipa"
admin.site.index_title = "Gestão do site"

# The technical admin has no protection against password guessing of its own, so
# its login page sends people to the panel login (attempt limits + lockout).
admin.site.login = RedirectView.as_view(pattern_name="panel:login", query_string=True)

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path(settings.PANEL_URL, include("panel.urls")),
    path("i18n/<str:lang_code>/", core_views.switch_language, name="switch_language"),
    path("robots.txt", core_views.robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="django.contrib.sitemaps.views.sitemap"),
    path("healthz/", core_views.healthz, name="healthz"),
]

urlpatterns += i18n_patterns(
    path("", include("core.urls")),
    path("", include("tours.urls")),
    path("", include("bookings.urls")),
    prefix_default_language=True,
)

if settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve_media, name="media"),
    ]
