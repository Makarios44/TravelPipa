from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache

from core.antispam import rate_limited
from core.context_processors import whatsapp_link
from core.forms import ReviewForm
from core.google_reviews import write_review_url
from core.i18n import current_suffix
from core.models import SiteSettings, Testimonial
from core.templatetags.travelpipa import money
from tours.models import Experience

from .forms import BookingRequestForm
from .models import BookingRequest
from .notifications import notify_new_booking, notify_new_review

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
    message = _("Hello! I just made booking %(ref)s for \"%(title)s\".") % {"ref": reference, "title": title}
    # Only non-personal information is shown on this page.
    return render(request, "bookings/booking_thanks.html", {
        "reference": reference,
        "experience_title": title,
        "round_trip": booking.round_trip,
        "quoted_total": money(booking.quoted_total, booking.experience.currency if booking.experience else "BRL")
        if booking.quoted_total is not None else "",
        "whatsapp_url": whatsapp_link(site, message),
    })


def suggested_display_name(full_name):
    parts = [p for p in (full_name or "").split() if p]
    if not parts:
        return ""
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0]}."


@never_cache
def review(request, token):
    """Personal review page of a booking: one review per booking, then the Google button."""
    booking = get_object_or_404(BookingRequest.objects.select_related("experience"), uuid=token)
    site = SiteSettings.load()
    existing = Testimonial.objects.filter(booking=booking).first()
    form = None
    if existing is None:
        if request.method == "POST":
            form = ReviewForm(request.POST)
            if rate_limited(request, "review"):
                form.add_error(None, _("Too many requests from this connection. Please try again later."))
            elif form.is_valid():
                data = form.cleaned_data
                lang = get_language() or "en"
                existing = Testimonial.objects.create(
                    author_name=data["author_name"].strip(), author_country=data["author_country"].strip(),
                    experience=booking.experience, rating=data["rating"],
                    **{f"text_{current_suffix(lang)}": data["text"].strip()},
                    source="TravelPipa", review_date=timezone.localdate(), language=lang,
                    booking=booking, from_customer=True, confirmed_real=True, active=False,
                )
                notify_new_review(request, existing)
                return redirect(request.path + "?ok=1")
        else:
            form = ReviewForm(initial={"author_name": suggested_display_name(booking.full_name), "rating": None})
    response = render(request, "bookings/review.html", {
        "form": form,
        "booking": booking,
        "experience_title": booking.experience.title if booking.experience else booking.experience_title,
        "review": existing,
        "just_sent": existing is not None and request.GET.get("ok") == "1",
        "google_review_url": write_review_url(site.google_place_id),
    })
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
