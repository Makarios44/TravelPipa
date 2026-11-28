"""
Trip vouchers for confirmed bookings.

* Customer voucher (customer's language): trip, driver/car if known, deposit paid
  and what is left to pay on the day.
* Driver voucher (Portuguese): trip, customer contact, total, deposit already paid
  and the amount the driver collects.

Both are pages opened by an unguessable link (booking.uuid / booking.driver_token)
and stop working 30 days after the trip.
"""
import datetime
import logging
import uuid
from urllib.parse import quote

from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils import timezone, translation

from core.models import SiteSettings
from core.templatetags.travelpipa import money

from .models import BookingRequest
from .notifications import email_configured, one_line

logger = logging.getLogger(__name__)

VALID_DAYS_AFTER_TRIP = 30

CLIENT = {
    "pt-br": {
        "title": "Voucher da viagem", "booking": "Reserva", "trip": "Viagem", "date": "Data",
        "return": "Volta", "time": "Horário", "from": "Embarque", "to": "Destino", "flight": "Voo",
        "people": "Pessoas", "name": "Nome", "driver": "Motorista", "car": "Carro", "plate": "Placa",
        "driver_soon": "Você recebe o nome do motorista, a placa e as fotos até 12 horas antes da viagem.",
        "total": "Valor total", "deposit": "Sinal pago", "due": "Restante a pagar no dia",
        "due_how": "Pago direto ao motorista ou guia, por Pix ou dinheiro.",
        "paid_full": "Tudo pago.", "help": "Dúvidas ou imprevistos? Fale com a gente",
        "print": "Imprimir / salvar em PDF", "datefmt": "%d/%m/%Y", "round": "ida e volta",
        "subject": "Voucher da sua viagem — reserva {ref}",
        "hello": "Olá, {name}!", "msg": "Sua viagem está confirmada. Aqui está o seu voucher, com os dados da viagem e os valores:",
        "bye": "Qualquer dúvida, é só responder esta mensagem.", "sign": "Equipe TravelPipa",
    },
    "en": {
        "title": "Trip voucher", "booking": "Booking", "trip": "Trip", "date": "Date",
        "return": "Return", "time": "Time", "from": "Pick-up", "to": "Destination", "flight": "Flight",
        "people": "People", "name": "Name", "driver": "Driver", "car": "Car", "plate": "Plate",
        "driver_soon": "You will receive the driver's name, the plate and photos up to 12 hours before the trip.",
        "total": "Total price", "deposit": "Deposit paid", "due": "Left to pay on the day",
        "due_how": "Paid directly to the driver or guide, by Pix or in cash.",
        "paid_full": "Fully paid.", "help": "Questions or last-minute changes? Talk to us",
        "print": "Print / save as PDF", "datefmt": "%m/%d/%Y", "round": "round trip",
        "subject": "Your trip voucher — booking {ref}",
        "hello": "Hi {name}!", "msg": "Your trip is confirmed. Here is your voucher with the trip details and amounts:",
        "bye": "If you have any questions, just reply to this message.", "sign": "The TravelPipa team",
    },
    "es": {
        "title": "Voucher del viaje", "booking": "Reserva", "trip": "Viaje", "date": "Fecha",
        "return": "Vuelta", "time": "Hora", "from": "Recogida", "to": "Destino", "flight": "Vuelo",
        "people": "Personas", "name": "Nombre", "driver": "Conductor", "car": "Coche", "plate": "Matrícula",
        "driver_soon": "Recibirás el nombre del conductor, la matrícula y las fotos hasta 12 horas antes del viaje.",
        "total": "Precio total", "deposit": "Seña pagada", "due": "Resta pagar el día del viaje",
        "due_how": "Se paga directamente al conductor o guía, con Pix o en efectivo.",
        "paid_full": "Todo pagado.", "help": "¿Dudas o imprevistos? Escríbenos",
        "print": "Imprimir / guardar en PDF", "datefmt": "%d/%m/%Y", "round": "ida y vuelta",
        "subject": "Voucher de tu viaje — reserva {ref}",
        "hello": "¡Hola, {name}!", "msg": "Tu viaje está confirmado. Aquí tienes tu voucher con los datos del viaje y los importes:",
        "bye": "Si tienes cualquier duda, responde a este mensaje.", "sign": "Equipo TravelPipa",
    },
}


def client_texts(booking):
    return CLIENT.get(booking.service_language, CLIENT["en"])


def trip_end(booking):
    return booking.return_date or booking.preferred_date


def is_available(booking):
    return (booking.status == BookingRequest.Status.CONFIRMED
            and timezone.localdate() <= trip_end(booking) + datetime.timedelta(days=VALID_DAYS_AFTER_TRIP))


def missing_for_voucher(booking):
    """What the team still has to fill in before sending vouchers (empty list = ready)."""
    missing = []
    if booking.status != BookingRequest.Status.CONFIRMED:
        missing.append("marcar a reserva como Confirmada")
    if booking.total_price is None:
        missing.append("valor total")
    if not booking.pickup_time:
        missing.append("horário de saída")
    if not booking.pickup_place:
        missing.append("local de embarque")
    return missing


def ensure_driver_token(booking):
    if not booking.driver_token:
        booking.driver_token = uuid.uuid4()
        booking.save(update_fields=["driver_token"])
    return booking.driver_token


def _absolute(path, request=None):
    if settings.SITE_URL:
        return settings.SITE_URL.rstrip("/") + path
    return request.build_absolute_uri(path) if request else path


def client_url(booking, request=None):
    return _absolute(reverse("voucher", args=[booking.uuid]), request)


def driver_url(booking, request=None):
    return _absolute(reverse("driver_voucher", args=[ensure_driver_token(booking)]), request)


def _title(booking, lang):
    exp = booking.experience
    if not exp:
        return booking.experience_title
    field = {"pt-br": "title_pt", "es": "title_es"}.get(lang, "title_en")
    return getattr(exp, field, "") or exp.title_en or booking.experience_title


def _brl(value, lang):
    with translation.override(lang):
        return money(value, "BRL")


def client_context(booking):
    lang = booking.service_language if booking.service_language in CLIENT else "en"
    t = CLIENT[lang]
    return {
        "t": t, "lang": lang, "booking": booking, "trip_title": _title(booking, lang),
        "date": booking.preferred_date.strftime(t["datefmt"]),
        "return_date": booking.return_date.strftime(t["datefmt"]) if booking.return_date else "",
        "total": _brl(booking.total_price, lang) if booking.total_price is not None else "",
        "deposit": _brl(booking.deposit_paid, lang),
        "due": _brl(booking.amount_due, lang) if booking.amount_due is not None else "",
        "paid_full": booking.amount_due == 0,
    }


def driver_context(booking):
    return {
        "booking": booking, "trip_title": _title(booking, "pt-br"),
        "date": booking.preferred_date.strftime("%d/%m/%Y"),
        "return_date": booking.return_date.strftime("%d/%m/%Y") if booking.return_date else "",
        "total": _brl(booking.total_price, "pt-br") if booking.total_price is not None else "",
        "deposit": _brl(booking.deposit_paid, "pt-br"),
        "due": _brl(booking.amount_due, "pt-br") if booking.amount_due is not None else "",
        "customer_whatsapp": f"https://wa.me/{booking.phone_digits}" if booking.phone_digits else "",
    }


def _summary_lines(booking):
    ctx, t = client_context(booking), client_texts(booking)
    lines = [f"{t['booking']}: {booking.reference}", f"{t['trip']}: {ctx['trip_title']}",
             f"{t['date']}: {ctx['date']}" + (f" {booking.pickup_time:%H:%M}" if booking.pickup_time else "")]
    if ctx["return_date"]:
        lines.append(f"{t['return']}: {ctx['return_date']}"
                     + (f" {booking.return_time:%H:%M}" if booking.return_time else ""))
    if booking.pickup_place:
        lines.append(f"{t['from']}: {booking.pickup_place}")
    if booking.dropoff_place:
        lines.append(f"{t['to']}: {booking.dropoff_place}")
    if ctx["total"]:
        lines += [f"{t['total']}: {ctx['total']}", f"{t['deposit']}: {ctx['deposit']}"]
        lines.append(t["paid_full"] if ctx["paid_full"] else f"{t['due']}: {ctx['due']} ({t['due_how']})")
    return lines


def client_message(booking, request=None):
    t = client_texts(booking)
    first = booking.full_name.split()[0] if booking.full_name else ""
    return "\n".join([t["hello"].format(name=first), "", t["msg"], "", *_summary_lines(booking), "",
                      f"{t['title']}: {client_url(booking, request)}", "", t["bye"]])


def driver_message(booking, request=None):
    ctx = driver_context(booking)
    lines = [f"Olá, {booking.driver_name.split()[0] if booking.driver_name else 'motorista'}! Nova viagem TravelPipa confirmada:",
             "", f"Reserva: {booking.reference}", f"Viagem: {ctx['trip_title']}",
             f"Data: {ctx['date']}" + (f" às {booking.pickup_time:%H:%M}" if booking.pickup_time else "")]
    if ctx["return_date"]:
        lines.append(f"Volta: {ctx['return_date']}" + (f" às {booking.return_time:%H:%M}" if booking.return_time else ""))
    lines += [f"Cliente: {booking.full_name} ({booking.people} pessoa{'s' if booking.people != 1 else ''})"]
    if booking.pickup_place:
        lines.append(f"Embarque: {booking.pickup_place}")
    if booking.dropoff_place:
        lines.append(f"Destino: {booking.dropoff_place}")
    if booking.flight_number:
        lines.append(f"Voo: {booking.flight_number}")
    if ctx["total"]:
        lines += ["", f"Valor total: {ctx['total']}", f"Sinal já pago: {ctx['deposit']}",
                  f"COBRAR DO CLIENTE: {ctx['due']}"]
    lines += ["", f"Voucher completo: {driver_url(booking, request)}"]
    return "\n".join(lines)


def client_whatsapp_url(booking, request=None):
    if not booking.phone_digits:
        return ""
    return f"https://wa.me/{booking.phone_digits}?text={quote(client_message(booking, request))}"


def driver_whatsapp_url(booking, request=None):
    digits = "".join(ch for ch in booking.driver_phone if ch.isdigit())
    if not digits:
        return ""
    if len(digits) in (10, 11):  # Brazilian number typed without the country code
        digits = "55" + digits
    return f"https://wa.me/{digits}?text={quote(driver_message(booking, request))}"


def send_client_email(booking, request=None):
    """E-mail the voucher link to the customer. Returns an error text or ""."""
    missing = missing_for_voucher(booking)
    if missing:
        return "Antes de enviar, preencha: " + ", ".join(missing) + "."
    if not email_configured():
        return "O envio de e-mails não está configurado no servidor (RESEND_API_KEY)."
    site = SiteSettings.load()
    t = client_texts(booking)
    message = EmailMessage(subject=one_line(t["subject"].format(ref=booking.reference)),
                           body=client_message(booking, request) + f"\n\n{t['sign']}",
                           from_email=settings.DEFAULT_FROM_EMAIL, to=[booking.email],
                           reply_to=[site.email] if site.email else None)
    try:
        message.send()
    except Exception:
        logger.exception("Could not e-mail the voucher for %s", booking.reference)
        return "Não foi possível enviar o e-mail agora. Tente de novo em alguns minutos."
    return ""
