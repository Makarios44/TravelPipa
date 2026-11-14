import secrets
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import TimeStampedModel

REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I to avoid confusion


def generate_reference():
    return "TP-" + "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(7))


class BookingRequest(TimeStampedModel):
    """A booking *request*. It is never confirmed automatically and no payment is taken."""

    class Status(models.TextChoices):
        PENDING = "pending", "Nova — falta contato (New)"
        CONTACTED = "contacted", "Contatado (Contacted)"
        CONFIRMED = "confirmed", "Confirmada (Confirmed)"
        REJECTED = "rejected", "Recusada (Rejected)"
        CANCELLED = "cancelled", "Cancelada (Cancelled)"

    class Language(models.TextChoices):
        EN = "en", "English"
        PT = "pt-br", "Português"
        ES = "es", "Español"

    uuid = models.UUIDField("identificador único", default=uuid.uuid4, unique=True, editable=False)
    reference = models.CharField("código da solicitação", max_length=12, unique=True, editable=False)
    experience = models.ForeignKey("tours.Experience", verbose_name="experiência", on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="booking_requests")
    experience_title = models.CharField("experiência (no momento do pedido)", max_length=150, blank=True,
                                        help_text="Guardado para manter o histórico se a experiência for excluída.")
    preferred_date = models.DateField("data do passeio / da ida")
    round_trip = models.BooleanField("ida e volta", default=False,
                                     help_text="Só para transfers: o cliente quer ida e volta (desconto negociado no contato).")
    return_date = models.DateField("data da volta", null=True, blank=True)
    people = models.PositiveSmallIntegerField("quantidade de pessoas",
                                              validators=[MinValueValidator(1), MaxValueValidator(60)])
    full_name = models.CharField("nome completo", max_length=150)
    email = models.EmailField("e-mail")
    phone = models.CharField("WhatsApp / telefone", max_length=40)
    service_language = models.CharField("idioma de atendimento", max_length=8, choices=Language.choices,
                                        default=Language.EN)
    site_language = models.CharField("idioma do site no envio", max_length=8, blank=True)
    notes = models.TextField("observações do cliente", blank=True)
    status = models.CharField("status", max_length=12, choices=Status.choices, default=Status.PENDING,
                              db_index=True)
    internal_notes = models.TextField("observações internas", blank=True,
                                      help_text="Visível apenas para a equipe.")
    consent_at = models.DateTimeField("consentimento LGPD em", null=True, blank=True)
    notification_sent = models.BooleanField("notificação enviada", default=False, editable=False)

    class Meta:
        verbose_name = "solicitação de reserva"
        verbose_name_plural = "solicitações de reserva"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["preferred_date"]),
        ]

    def __str__(self):
        return f"{self.reference} — {self.full_name}"

    def save(self, *args, **kwargs):
        if not self.reference:
            ref = generate_reference()
            while BookingRequest.objects.filter(reference=ref).exists():
                ref = generate_reference()
            self.reference = ref
        if self.experience_id and not self.experience_title:
            self.experience_title = self.experience.title_en
        super().save(*args, **kwargs)

    @property
    def status_label(self):
        """Portuguese status name only, e.g. "Nova — falta contato"."""
        return self.get_status_display().split(" (")[0]

    @property
    def phone_digits(self):
        return "".join(ch for ch in self.phone if ch.isdigit())
