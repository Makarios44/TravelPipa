"""
Mercado Pago Checkout Pro: the customer pays the booking deposit on Mercado Pago's own
page (Pix, card or boleto) and comes back to the site. No card data ever reaches us.

Security rule: a payment is only trusted after the site asks Mercado Pago itself
(GET /v1/payments/<id> with our access token) and checks that it belongs to this
booking, is in BRL and covers the deposit. Notifications and return URLs only
tell us *which* payment to check.
"""
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

API = "https://api.mercadopago.com"

STATUS_MAP = {
    "approved": "paid",
    "authorized": "in_process",
    "in_process": "in_process",
    "in_mediation": "in_process",
    "pending": "in_process",
    "rejected": "rejected",
    "cancelled": "cancelled",
    "refunded": "refunded",
    "charged_back": "refunded",
}


class MercadoPagoError(Exception):
    pass


def configured():
    return bool(settings.MERCADOPAGO_ACCESS_TOKEN)


def deposit_for(total):
    if total is None:
        return None
    value = (Decimal(total) * Decimal(settings.DEPOSIT_PERCENT) / Decimal(100)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    return value if value > 0 else None


def _call(method, path, body=None, idempotency_key=None):
    headers = {
        "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "TravelPipa/1.0",
    }
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:400]
        logger.error("Mercado Pago %s %s -> %s: %s", method, path, exc.code, detail)
        raise MercadoPagoError(f"HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        logger.exception("Could not reach Mercado Pago")
        raise MercadoPagoError(str(exc)) from exc


def create_preference(booking, return_url, notification_url):
    """Creates the Checkout Pro preference for the deposit and stores its link on the booking."""
    title = booking.experience.title_pt if booking.experience else booking.experience_title
    first_name = (booking.full_name.split() or [""])[0]
    body = {
        "items": [{
            "id": booking.reference,
            "title": f"Sinal de {settings.DEPOSIT_PERCENT}% — {title}"[:250],
            "description": f"Reserva {booking.reference} — TravelPipa",
            "quantity": 1,
            "currency_id": "BRL",
            "unit_price": float(booking.deposit_amount),
        }],
        "payer": {"email": booking.email, "name": first_name},
        "external_reference": str(booking.uuid),
        "back_urls": {"success": return_url, "failure": return_url, "pending": return_url},
        "notification_url": notification_url,
        "statement_descriptor": "TRAVELPIPA",
        "metadata": {"booking": booking.reference},
    }
    if return_url.startswith("https://"):
        body["auto_return"] = "approved"
    data = _call("POST", "/checkout/preferences", body,
                 idempotency_key=f"{booking.uuid}-{booking.deposit_amount}")
    test_mode = settings.MERCADOPAGO_ACCESS_TOKEN.startswith("TEST-")
    link = (data.get("sandbox_init_point") if test_mode else None) or data.get("init_point") or ""
    if not link:
        raise MercadoPagoError("Mercado Pago did not return a payment link")
    booking.mp_preference_id = str(data.get("id") or "")[:80]
    booking.mp_init_point = link
    if booking.payment_status in ("", "rejected", "cancelled"):
        booking.payment_status = "waiting"
    booking.save(update_fields=["mp_preference_id", "mp_init_point", "payment_status", "updated_at"])
    return link


def sync_payment(payment_id, expected_booking=None):
    """
    Asks Mercado Pago about this payment and updates the booking it belongs to.
    Returns (booking, newly_paid). Raises MercadoPagoError if Mercado Pago can't be reached.
    """
    from .models import BookingRequest

    payment_id = "".join(ch for ch in str(payment_id or "") if ch.isdigit())[:40]
    if not payment_id:
        return None, False
    data = _call("GET", f"/v1/payments/{payment_id}")
    reference = str(data.get("external_reference") or "")
    with transaction.atomic():
        booking = BookingRequest.objects.select_for_update().filter(uuid=reference).first() if reference else None
        if booking is None:
            logger.warning("Mercado Pago payment %s has no matching booking (%r)", payment_id, reference)
            return None, False
        if expected_booking is not None and booking.pk != expected_booking.pk:
            logger.warning("Payment %s belongs to another booking; ignored", payment_id)
            return None, False
        status = STATUS_MAP.get(data.get("status"), "")
        amount = Decimal(str(data.get("transaction_amount") or "0"))
        if status == "paid" and (data.get("currency_id") != "BRL"
                                 or (booking.deposit_amount and amount < booking.deposit_amount)):
            logger.error("Payment %s for %s does not cover the deposit (%s %s); not marked as paid",
                         payment_id, booking.reference, amount, data.get("currency_id"))
            status = "in_process"
        if not status:
            return booking, False
        # A later "pending" or "rejected" attempt never undoes a deposit that was already paid.
        if booking.payment_status == "paid" and status not in ("paid", "refunded"):
            return booking, False
        newly_paid = status == "paid" and booking.payment_status != "paid"
        booking.payment_status = status
        booking.mp_payment_id = payment_id
        if status == "paid":
            booking.paid_amount = amount
            booking.paid_at = booking.paid_at or timezone.now()
        booking.save(update_fields=["payment_status", "mp_payment_id", "paid_amount", "paid_at", "updated_at"])
    return booking, newly_paid


def valid_signature(request, data_id):
    """Optional check of Mercado Pago's x-signature header (only when a secret is configured)."""
    secret = settings.MERCADOPAGO_WEBHOOK_SECRET
    if not secret:
        return True
    header = request.headers.get("x-signature", "")
    parts = dict(p.strip().split("=", 1) for p in header.split(",") if "=" in p)
    ts, v1 = parts.get("ts", ""), parts.get("v1", "")
    if not (ts and v1):
        return False
    manifest = f"id:{str(data_id).lower()};request-id:{request.headers.get('x-request-id', '')};ts:{ts};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)
