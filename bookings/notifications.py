import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils import timezone

from core.models import SiteSettings

logger = logging.getLogger(__name__)


def absolute(request, path):
    return (settings.SITE_URL + path) if settings.SITE_URL else request.build_absolute_uri(path)


def notification_recipients():
    recipients = list(settings.NOTIFICATION_EMAILS)
    if not recipients:
        site = SiteSettings.load()
        if site.email:
            recipients = [site.email]
    return recipients


def email_configured():
    return settings.EMAIL_ENABLED


def one_line(text, limit=150):
    """Subjects come partly from visitors: no line breaks (header injection) and a sane length."""
    return " ".join(str(text or "").split())[:limit]


def send(subject, body, recipients, reply_to=None):
    EmailMessage(subject=one_line(subject), body=body, from_email=settings.DEFAULT_FROM_EMAIL,
                 to=recipients, reply_to=[reply_to] if reply_to else None).send()


def notify_new_booking(request, booking):
    """E-mail the team about a new request. Silently skipped when SMTP is not configured."""
    recipients = notification_recipients()
    if not email_configured() or not recipients:
        logger.info("Booking %s saved; e-mail notification skipped (e-mail or recipient not configured).",
                    booking.reference)
        return False
    panel_url = absolute(request, reverse("panel:booking_detail", args=[booking.pk]))
    created = timezone.localtime(booking.created_at)
    body = "\n".join([
        "Nova solicitação de reserva recebida pelo site.",
        "",
        f"Código: {booking.reference}",
        f"Experiência: {booking.experience_title}",
        f"Data pretendida: {booking.preferred_date:%d/%m/%Y}",
        f"Pessoas: {booking.people}",
        f"Cliente: {booking.full_name}",
        f"E-mail: {booking.email}",
        f"WhatsApp/telefone: {booking.phone}",
        f"Idioma de atendimento: {booking.get_service_language_display()}",
        f"Observações: {booking.notes or '—'}",
        f"Recebida em: {created:%d/%m/%Y %H:%M}",
        "",
        f"Abrir no painel: {panel_url}",
        "",
        "Lembre-se: a solicitação NÃO está confirmada. Entre em contato com o cliente.",
        "Responder este e-mail envia a resposta direto para o cliente.",
    ])
    try:
        send(f"[TravelPipa] Nova solicitação {booking.reference} — {booking.experience_title}",
             body, recipients, reply_to=booking.email)
    except Exception:
        logger.exception("Could not send notification for booking %s", booking.reference)
        return False
    booking.notification_sent = True
    booking.save(update_fields=["notification_sent"])
    return True


def notify_new_contact(request, message):
    recipients = notification_recipients()
    if not email_configured() or not recipients:
        return False
    panel_url = absolute(request, reverse("panel:messages"))
    body = (f"Nova mensagem de contato.\n\nNome: {message.name}\nE-mail: {message.email}\n"
            f"Telefone: {message.phone or '—'}\nIdioma: {message.language}\nAssunto: {message.subject or '—'}\n\n"
            f"{message.message}\n\nAbrir no painel: {panel_url}")
    try:
        send(f"[TravelPipa] Contato: {message.subject or message.name}", body, recipients,
             reply_to=message.email)
        return True
    except Exception:
        logger.exception("Could not send contact notification")
        return False
