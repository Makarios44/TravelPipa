import secrets
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import IMAGE_VALIDATORS, TimeStampedModel

REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I to avoid confusion


def driver_upload_to(instance, filename):
    """Random names: these photos are only shared with the customer of the booking."""
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "jpg").lower()[:5]
    return f"drivers/{uuid.uuid4().hex}.{ext}"


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
                                     help_text="Só para transfers: o cliente quer ida e volta.")
    return_date = models.DateField("data da volta", null=True, blank=True)
    quoted_total = models.DecimalField(
        "valor mostrado ao cliente", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Total calculado pelo site no momento da reserva (transfers com tabela de preços).")
    quote_summary = models.CharField("resumo do valor", max_length=200, blank=True,
                                     help_text="Ex.: 2 carros (3 + 3) · ida e volta · R$ 460 por trecho")

    # --- Deposit paid online (Mercado Pago Checkout Pro) --------------------------
    class PaymentStatus(models.TextChoices):
        NONE = "", "Sem cobrança online"
        WAITING = "waiting", "Link gerado — aguardando pagamento"
        IN_PROCESS = "in_process", "Pagamento em análise"
        PAID = "paid", "Sinal pago"
        REJECTED = "rejected", "Pagamento recusado"
        CANCELLED = "cancelled", "Pagamento cancelado"
        REFUNDED = "refunded", "Pagamento devolvido"

    deposit_amount = models.DecimalField(
        "valor do sinal", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Calculado como 10% do valor mostrado ao cliente. Pode ser ajustado antes de enviar o link.")
    payment_status = models.CharField("pagamento do sinal", max_length=12, choices=PaymentStatus.choices,
                                      blank=True, default=PaymentStatus.NONE, db_index=True)
    mp_preference_id = models.CharField("Mercado Pago — preferência", max_length=80, blank=True, editable=False)
    mp_init_point = models.URLField("Mercado Pago — link de pagamento", max_length=500, blank=True, editable=False)
    mp_payment_id = models.CharField("Mercado Pago — pagamento", max_length=40, blank=True, editable=False)
    paid_amount = models.DecimalField("valor pago", max_digits=10, decimal_places=2, null=True, blank=True,
                                      editable=False)
    paid_at = models.DateTimeField("sinal pago em", null=True, blank=True, editable=False)
    # Driver and car, sent to the customer up to 12 hours before the trip.
    driver_name = models.CharField("nome do motorista", max_length=80, blank=True)
    driver_phone = models.CharField("WhatsApp do motorista", max_length=30, blank=True,
                                    help_text="Opcional. Só envie se o motorista concordar.")
    vehicle_model = models.CharField("carro (modelo e cor)", max_length=60, blank=True,
                                     help_text="Ex.: BYD Song Pro branco")
    vehicle_plate = models.CharField("placa", max_length=10, blank=True)
    vehicle_der = models.BooleanField("veículo cadastrado no DER/RN", default=False,
                                      help_text="Marque só se este carro tem o certificado do DER/RN. "
                                                "A mensagem ao cliente cita o DER/RN apenas quando marcado.")
    driver_photo = models.ImageField("foto do motorista", upload_to=driver_upload_to, blank=True,
                                     validators=IMAGE_VALIDATORS)
    vehicle_photo = models.ImageField("foto do carro", upload_to=driver_upload_to, blank=True,
                                      validators=IMAGE_VALIDATORS)
    driver_sent_at = models.DateTimeField("motorista enviado ao cliente em", null=True, blank=True,
                                          editable=False)
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
    def has_driver(self):
        return bool(self.driver_name and self.vehicle_plate)

    @property
    def phone_digits(self):
        return "".join(ch for ch in self.phone if ch.isdigit())
