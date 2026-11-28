import json

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
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

from . import mercadopago, voucher as vouchers
from .forms import BookingRequestForm
from .models import BookingRequest
from .notifications import absolute, notify_deposit_paid, notify_new_booking, notify_new_review

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
        "is_transfer": bool(booking.experience and booking.experience.is_transfer),
        "quoted_total": money(booking.quoted_total, booking.experience.currency if booking.experience else "BRL")
        if booking.quoted_total is not None else "",
        "whatsapp_url": whatsapp_link(site, message),
        **_deposit_context(booking),
    })


def _deposit_context(booking):
    if not (mercadopago.configured() and booking.deposit_amount):
        return {}
    currency = booking.experience.currency if booking.experience else "BRL"
    return {"deposit_url": reverse("bookings:deposit", args=[booking.uuid]),
            "deposit": money(booking.deposit_amount, currency)}


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


def _deposit_urls(request, booking):
    lang = get_language() or "en"
    with translation.override(lang):
        page = reverse("bookings:deposit", args=[booking.uuid])
    return absolute(request, page), absolute(request, reverse("mercadopago_webhook"))


@never_cache
def deposit(request, token):
    """Customer page of the booking deposit: pay with Mercado Pago, or see that it is paid."""
    booking = get_object_or_404(BookingRequest.objects.select_related("experience"), uuid=token)
    payment_id = request.GET.get("payment_id") or request.GET.get("collection_id")
    if payment_id and mercadopago.configured() and booking.payment_status != BookingRequest.PaymentStatus.PAID:
        try:
            newly_paid = mercadopago.sync_payment(payment_id, expected_booking=booking)[1]
        except mercadopago.MercadoPagoError:
            newly_paid = False
        booking.refresh_from_db()
        if newly_paid:
            notify_deposit_paid(request, booking)

    closed = booking.status in (BookingRequest.Status.REJECTED, BookingRequest.Status.CANCELLED)
    paid = booking.payment_status == BookingRequest.PaymentStatus.PAID
    can_pay = (mercadopago.configured() and booking.deposit_amount and not closed and not paid
               and booking.payment_status != BookingRequest.PaymentStatus.REFUNDED)
    pay_url, error = "", False
    if can_pay:
        pay_url = booking.mp_init_point
        if not pay_url:
            return_url, webhook_url = _deposit_urls(request, booking)
            try:
                pay_url = mercadopago.create_preference(booking, return_url, webhook_url)
            except mercadopago.MercadoPagoError:
                error = True
    site = SiteSettings.load()
    title = booking.experience.title if booking.experience else booking.experience_title
    message = _("Hello! I have a question about the deposit of booking %(ref)s.") % {"ref": booking.reference}
    currency = booking.experience.currency if booking.experience else "BRL"
    response = render(request, "bookings/deposit.html", {
        "booking": booking,
        "experience_title": title,
        "deposit": money(booking.deposit_amount, currency) if booking.deposit_amount else "",
        "total": money(booking.quoted_total, currency) if booking.quoted_total else "",
        "paid": paid,
        "closed": closed,
        "pay_url": pay_url,
        "error": error,
        "status": request.GET.get("status") or booking.payment_status,
        "whatsapp_url": whatsapp_link(site, message),
    })
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@csrf_exempt
@require_http_methods(["GET", "POST"])
def mercadopago_webhook(request):
    """Mercado Pago tells us that a payment changed; we ask Mercado Pago what happened."""
    if not mercadopago.configured():
        return HttpResponse(status=200)
    try:
        payload = json.loads(request.body or b"{}") if request.method == "POST" else {}
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    kind = payload.get("type") or payload.get("topic") or request.GET.get("type") or request.GET.get("topic")
    data_id = ((payload.get("data") or {}).get("id") if isinstance(payload.get("data"), dict) else None) \
        or request.GET.get("data.id") or request.GET.get("id")
    if kind != "payment" or not data_id:
        return HttpResponse(status=200)  # other topics (merchant orders, tests) are not needed
    if not mercadopago.valid_signature(request, request.GET.get("data.id") or data_id):
        return HttpResponse(status=401)
    try:
        booking, newly_paid = mercadopago.sync_payment(data_id)
    except mercadopago.MercadoPagoError:
        return HttpResponse(status=502)  # Mercado Pago tries again later
    if newly_paid:
        notify_deposit_paid(request, booking)
    return HttpResponse(status=200)


def _voucher_response(request, booking, context):
    response = render(request, "bookings/voucher.html", context)
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@never_cache
def voucher(request, token):
    """Customer voucher, in the customer's language."""
    booking = get_object_or_404(BookingRequest.objects.select_related("experience"), uuid=token)
    if not vouchers.is_available(booking):
        raise Http404
    site = SiteSettings.load()
    ctx = vouchers.client_context(booking)
    ctx.update({"labels": ctx["t"], "heading": ctx["t"]["title"], "is_driver": False, "site": site,
                "help_url": whatsapp_link(site, f"{booking.reference}")})
    return _voucher_response(request, booking, ctx)


@never_cache
def driver_voucher(request, token):
    """Driver voucher (Portuguese): customer contact and the amount to collect."""
    booking = BookingRequest.objects.select_related("experience").filter(driver_token=token).first()
    if not booking or not vouchers.is_available(booking):
        raise Http404
    ctx = vouchers.driver_context(booking)
    labels = dict(vouchers.CLIENT["pt-br"], deposit="Sinal já pago", due="Cobrar do cliente no dia",
                  due_how="Receber por Pix ou dinheiro.", name="Cliente")
    ctx.update({"labels": labels, "heading": "Voucher da viagem", "is_driver": True, "lang": "pt-br",
                "paid_full": booking.amount_due == 0})
    return _voucher_response(request, booking, ctx)
