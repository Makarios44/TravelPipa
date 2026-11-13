from django.urls import path
from django.utils.translation import gettext_lazy as _

from . import views

app_name = "bookings"

urlpatterns = [
    path(_("book/"), views.booking_request, name="request"),
    path(_("book/thanks/"), views.booking_thanks, name="thanks"),
]
