"""
Message telling the customer who the driver is: name, car, plate (and photos by e-mail).
Written in the customer's service language; the DER/RN line only appears when the
team ticked that this specific car is registered.
"""
import logging
import mimetypes
from urllib.parse import quote

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from core.models import SiteSettings

from .notifications import email_configured, one_line

logger = logging.getLogger(__name__)

TEXTS = {
    "pt-br": {
        "subject": "Seu motorista para a reserva {ref} — TravelPipa",
        "hello": "Olá, {name}!",
        "intro": "Sua reserva {ref} ({title}) do dia {date} está confirmada. Estes são os dados do seu motorista:",
        "driver": "Motorista: {v}",
        "car": "Carro: {v}",
        "plate": "Placa: {v}",
        "phone": "WhatsApp do motorista: {v}",
        "der": "Veículo cadastrado no DER/RN para transporte turístico.",
        "photos": "As fotos do motorista e do carro estão em anexo.",
        "photos_wa": "Em seguida enviamos aqui as fotos do motorista e do carro.",
        "bye": "Qualquer dúvida, é só responder esta mensagem. Boa viagem!",
        "sign": "Equipe TravelPipa",
        "date": "%d/%m/%Y",
    },
    "en": {
        "subject": "Your driver for booking {ref} — TravelPipa",
        "hello": "Hi {name}!",
        "intro": "Your booking {ref} ({title}) on {date} is confirmed. Here are your driver's details:",
        "driver": "Driver: {v}",
        "car": "Car: {v}",
        "plate": "Plate: {v}",
        "phone": "Driver's WhatsApp: {v}",
        "der": "Vehicle registered with DER/RN (Rio Grande do Norte transport authority) for tourist transport.",
        "photos": "Photos of the driver and the car are attached.",
        "photos_wa": "We'll send the photos of the driver and the car right after this message.",
        "bye": "If you have any questions, just reply to this message. Have a great trip!",
        "sign": "The TravelPipa team",
        "date": "%m/%d/%Y",
    },
    "es": {
        "subject": "Tu conductor para la reserva {ref} — TravelPipa",
        "hello": "¡Hola, {name}!",
        "intro": "Tu reserva {ref} ({title}) del día {date} está confirmada. Estos son los datos de tu conductor:",
        "driver": "Conductor: {v}",
        "car": "Coche: {v}",
        "plate": "Matrícula: {v}",
        "phone": "WhatsApp del conductor: {v}",
        "der": "Vehículo registrado en el DER/RN (órgano de transporte de Rio Grande do Norte) para transporte turístico.",
        "photos": "Las fotos del conductor y del coche van adjuntas.",
        "photos_wa": "A continuación te enviamos por aquí las fotos del conductor y del coche.",
        "bye": "Si tienes cualquier duda, responde a este mensaje. ¡Buen viaje!",
        "sign": "Equipo TravelPipa",
        "date": "%d/%m/%Y",
    },
}


def _texts(booking):
    return TEXTS.get(booking.service_language, TEXTS["en"])


def _title(booking):
    exp = booking.experience
    if not exp:
        return booking.experience_title
    field = {"pt-br": "title_pt", "es": "title_es"}.get(booking.service_language, "title_en")
    return getattr(exp, field, "") or exp.title_en or booking.experience_title


def _has_photos(booking):
    return bool(booking.driver_photo or booking.vehicle_photo)


def message_body(booking, channel="email"):
    t = _texts(booking)
    first_name = booking.full_name.split()[0] if booking.full_name else ""
    lines = [t["hello"].format(name=first_name), "",
             t["intro"].format(ref=booking.reference, title=_title(booking),
                               date=booking.preferred_date.strftime(t["date"])),
             "", t["driver"].format(v=booking.driver_name)]
    if booking.vehicle_model:
        lines.append(t["car"].format(v=booking.vehicle_model))
    lines.append(t["plate"].format(v=booking.vehicle_plate))
    if booking.driver_phone:
        lines.append(t["phone"].format(v=booking.driver_phone))
    if booking.vehicle_der:
        lines.append(t["der"])
    if _has_photos(booking):
        lines += ["", t["photos"] if channel == "email" else t["photos_wa"]]
    lines += ["", t["bye"]]
    if channel == "email":
        lines += ["", t["sign"]]
    return "\n".join(lines)


def whatsapp_url(booking):
    if not (booking.has_driver and booking.phone_digits):
        return ""
    return f"https://wa.me/{booking.phone_digits}?text={quote(message_body(booking, 'whatsapp'))}"


def _attach(message, field, label):
    if not field:
        return
    try:
        field.open("rb")
        content = field.read()
    finally:
        try:
            field.close()
        except Exception:  # pragma: no cover - storage specific
            pass
    ext = field.name.rsplit(".", 1)[-1].lower() if "." in field.name else "jpg"
    message.attach(f"{label}.{ext}", content, mimetypes.guess_type(field.name)[0] or "image/jpeg")


def send_email(booking):
    """E-mail the driver details (with photos) to the customer. Returns an error text or ""."""
    if not booking.has_driver:
        return "Preencha pelo menos o nome do motorista e a placa."
    if not email_configured():
        return "O envio de e-mails não está configurado no servidor (RESEND_API_KEY)."
    site = SiteSettings.load()
    t = _texts(booking)
    message = EmailMessage(subject=one_line(t["subject"].format(ref=booking.reference)),
                           body=message_body(booking, "email"), from_email=settings.DEFAULT_FROM_EMAIL,
                           to=[booking.email], reply_to=[site.email] if site.email else None)
    labels = {"pt-br": ("motorista", "carro"), "es": ("conductor", "coche")}.get(
        booking.service_language, ("driver", "car"))
    _attach(message, booking.driver_photo, labels[0])
    _attach(message, booking.vehicle_photo, labels[1])
    try:
        message.send()
    except Exception:
        logger.exception("Could not e-mail the driver details for %s", booking.reference)
        return "Não foi possível enviar o e-mail agora. Tente de novo em alguns minutos."
    booking.driver_sent_at = timezone.now()
    booking.save(update_fields=["driver_sent_at"])
    return ""
