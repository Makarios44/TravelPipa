from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache

from core.antispam import rate_limited
from core.context_processors import whatsapp_link
from core.models import SiteSettings
from tours.models import Experience

from .forms import BookingRequestForm
from .models import BookingRequest
from .notifications import notify_new_booking

SESSION_KEY = "last_booking_reference"


@never_cache
def booking_request(request):
    preselected = None
    slug = request.GET.get("experience", "").strip()
    if slug:
        preselected = Experience.objects.published().filter(slug=slug).first()

    if request.method == "POST":
        form = BookingRequestForm(request.POST)
        if rate_limited(request, "booking"):
            form.add_error(None, _("Too many requests from this connection. Please try again later or contact us on WhatsApp."))
        elif form.is_valid():
            booking = form.save()
            notify_new_booking(request, booking)
            request.session[SESSION_KEY] = booking.reference
            return redirect("bookings:thanks")
        preselected = form.cleaned_data.get("experience") if hasattr(form, "cleaned_data") else preselected
    else:
        initial = {"experience": preselected.pk} if preselected else {}
        form = BookingRequestForm(initial=initial)

    return render(request, "bookings/booking_form.html", {"form": form, "preselected": preselected})


@never_cache
def booking_thanks(request):
    reference = request.session.get(SESSION_KEY)
    if not reference:
        return redirect("bookings:request")
    booking = BookingRequest.objects.filter(reference=reference).select_related("experience").first()
    if not booking:
        return redirect("bookings:request")
    site = SiteSettings.load()
    title = booking.experience.title if booking.experience else booking.experience_title
    message = _("Hello! I just sent booking request %(ref)s for \"%(title)s\".") % {"ref": reference, "title": title}
    # Only non-personal information is shown on this page.
    return render(request, "bookings/booking_thanks.html", {
        "reference": reference,
        "experience_title": title,
        "whatsapp_url": whatsapp_link(site, message),
    })
