from django.urls import path
from django.utils.translation import gettext_lazy as _

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path(_("about/"), views.about, name="about"),
    path(_("contact/"), views.contact, name="contact"),
    path(_("privacy-policy/"), views.privacy, name="privacy"),
    path(_("terms-and-conditions/"), views.terms, name="terms"),
    path(_("tides-and-weather/"), views.tides_weather, name="tides_weather"),
    path(_("reviews/"), views.reviews, name="reviews"),
    path("widgets/conditions/", views.conditions_widget, name="conditions_widget"),
    path("widgets/google-reviews/", views.google_reviews_widget, name="google_reviews_widget"),
]
