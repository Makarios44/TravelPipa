from django.urls import path
from django.utils.translation import gettext_lazy as _

from . import views

app_name = "tours"

urlpatterns = [
    path(_("experiences/"), views.experience_list, name="experience_list"),
    path(_("experiences/<slug:slug>/"), views.experience_detail, name="experience_detail"),
    path(_("transfers/"), views.transfers, name="transfers"),
]
