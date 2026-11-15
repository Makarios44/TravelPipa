import re

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models

from .i18n import Localized, lines
from .images import ALLOWED_EXTENSIONS, optimize_image_field, validate_image_size

IMAGE_VALIDATORS = [FileExtensionValidator(ALLOWED_EXTENSIONS), validate_image_size]


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        abstract = True


def validate_whatsapp(value):
    digits = re.sub(r"\D", "", value or "")
    if value and not (10 <= len(digits) <= 15):
        raise ValidationError("Informe o número com código do país e DDD, ex.: +55 84 99999-9999.")


def text_field(label, lang, blank=True, **kw):
    return models.TextField(f"{label} ({lang})", blank=blank, **kw)


def char_field(label, lang, max_length=200, blank=True, **kw):
    return models.CharField(f"{label} ({lang})", max_length=max_length, blank=blank, **kw)


class SiteSettings(TimeStampedModel):
    """Single row with all institutional information editable in the admin."""

    CACHE_KEY = "site_settings"

    site_name = models.CharField("nome do site", max_length=80, default="TravelPipa")
    logo = models.ImageField("logotipo", upload_to="site/", blank=True, validators=IMAGE_VALIDATORS,
                             help_text="Opcional. Sem logotipo, o nome é exibido em texto.")
    hero_image = models.ImageField("foto do banner principal", upload_to="site/", blank=True,
                                   validators=IMAGE_VALIDATORS,
                                   help_text="Foto panorâmica real de Praia da Pipa, horizontal, mín. 1920px de largura.")
    about_image = models.ImageField("foto da seção sobre Pipa", upload_to="site/", blank=True,
                                    validators=IMAGE_VALIDATORS)
    og_image = models.ImageField("imagem de compartilhamento (redes sociais)", upload_to="site/", blank=True,
                                 validators=IMAGE_VALIDATORS, help_text="1200×630 px recomendado.")

    # Contact
    whatsapp = models.CharField("WhatsApp", max_length=30, blank=True, validators=[validate_whatsapp],
                                help_text="Com código do país, ex.: +55 84 99999-9999.")
    phone = models.CharField("telefone", max_length=30, blank=True)
    email = models.EmailField("e-mail de contato", blank=True,
                              help_text="Também recebe as notificações de novas solicitações.")
    instagram = models.URLField("Instagram (URL)", blank=True)
    facebook = models.URLField("Facebook (URL)", blank=True)
    tiktok = models.URLField("TikTok (URL)", blank=True)
    youtube = models.URLField("YouTube (URL)", blank=True)
    tripadvisor = models.URLField("Tripadvisor (URL)", blank=True)
    address = models.CharField("endereço", max_length=255, blank=True)
    google_maps_url = models.URLField("link do Google Maps", blank=True)
    company_legal_name = models.CharField("razão social", max_length=150, blank=True)
    company_document = models.CharField("CNPJ", max_length=30, blank=True)
    google_place_id = models.CharField(
        "Google Place ID", max_length=200, blank=True,
        help_text="Identificador do Perfil da Empresa no Google (começa com ChIJ...). Usado no botão "
                  "\"Avaliar no Google\" e para mostrar as avaliações do Google no site.")
    trust_cadastur_guides = models.BooleanField(
        "selo: guias de turismo com Cadastur", default=True,
        help_text="Exibe no site que os guias de turismo são cadastrados no Cadastur (Ministério do Turismo).")
    trust_der_vehicles = models.BooleanField(
        "selo: veículos cadastrados no DER/RN", default=True,
        help_text="Exibe no site que os veículos são cadastrados para transporte turístico no DER/RN.")
    cadastur = models.CharField("número Cadastur", max_length=40, blank=True,
                                help_text="Preencha apenas se a agência possuir registro.")

    # Localised institutional texts
    opening_hours_en = char_field("Horário de atendimento", "EN", 200)
    opening_hours_pt = char_field("Horário de atendimento", "PT", 200)
    opening_hours_es = char_field("Horário de atendimento", "ES", 200)

    about_intro_en = text_field("Sobre — resumo (página inicial)", "EN")
    about_intro_pt = text_field("Sobre — resumo (página inicial)", "PT")
    about_intro_es = text_field("Sobre — resumo (página inicial)", "ES")

    about_body_en = text_field("Página Sobre — texto completo", "EN",
                               help_text="Parágrafos separados por linha em branco.")
    about_body_pt = text_field("Página Sobre — texto completo", "PT")
    about_body_es = text_field("Página Sobre — texto completo", "ES")

    pipa_region_en = text_field("Seção sobre a região de Pipa", "EN")
    pipa_region_pt = text_field("Seção sobre a região de Pipa", "PT")
    pipa_region_es = text_field("Seção sobre a região de Pipa", "ES")

    default_cancellation_en = text_field("Política de cancelamento padrão", "EN")
    default_cancellation_pt = text_field("Política de cancelamento padrão", "PT")
    default_cancellation_es = text_field("Política de cancelamento padrão", "ES")

    privacy_policy_en = text_field("Política de privacidade", "EN",
                                   help_text="Vazio = texto-modelo padrão. Revise com seu jurídico.")
    privacy_policy_pt = text_field("Política de privacidade", "PT")
    privacy_policy_es = text_field("Política de privacidade", "ES")

    terms_en = text_field("Termos e condições", "EN", help_text="Vazio = texto-modelo padrão.")
    terms_pt = text_field("Termos e condições", "PT")
    terms_es = text_field("Termos e condições", "ES")

    opening_hours = Localized()
    about_intro = Localized()
    about_body = Localized()
    pipa_region = Localized()
    default_cancellation = Localized()
    privacy_policy = Localized(fallback=False)
    terms = Localized(fallback=False)

    class Meta:
        verbose_name = "configurações do site"
        verbose_name_plural = "configurações do site"

    def __str__(self):
        return "Configurações do site"

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        if not self.created_at:
            existing = type(self).objects.filter(pk=1).values_list("created_at", flat=True).first()
            if existing:
                self.created_at = existing
                self._state.adding = False
        for field in ("logo", "hero_image", "about_image"):
            optimize_image_field(getattr(self, field))
        optimize_image_field(self.og_image, max_side=1200)
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    def delete(self, *args, **kwargs):  # the settings row cannot be deleted
        return

    @classmethod
    def load(cls):
        obj = cache.get(cls.CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(cls.CACHE_KEY, obj, 300)
        return obj

    @property
    def whatsapp_digits(self):
        return re.sub(r"\D", "", self.whatsapp or "")

    @property
    def social_links(self):
        items = [
            ("instagram", "Instagram", self.instagram),
            ("facebook", "Facebook", self.facebook),
            ("tiktok", "TikTok", self.tiktok),
            ("youtube", "YouTube", self.youtube),
            ("tripadvisor", "Tripadvisor", self.tripadvisor),
        ]
        return [{"icon": icon, "name": name, "url": url} for icon, name, url in items if url]

    @property
    def about_paragraphs(self):
        return [p.strip() for p in (self.about_body or "").split("\n\n") if p.strip()]

    @property
    def pipa_paragraphs(self):
        return [p.strip() for p in (self.pipa_region or "").split("\n\n") if p.strip()]


class TestimonialQuerySet(models.QuerySet):
    def published(self):
        return self.filter(active=True, confirmed_real=True)

    def awaiting_approval(self):
        return self.filter(from_customer=True, active=False)

    def for_language(self, suffix):
        return self.published().exclude(**{f"text_{suffix}": ""})


class Testimonial(TimeStampedModel):
    """Real customer reviews only. The section is hidden while none exist."""

    author_name = models.CharField("nome do cliente", max_length=120)
    author_country = models.CharField("país / cidade", max_length=80, blank=True)
    experience = models.ForeignKey("tours.Experience", verbose_name="experiência", on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="testimonials")
    rating = models.PositiveSmallIntegerField("nota (1–5)", null=True, blank=True,
                                              validators=[MinValueValidator(1), MaxValueValidator(5)])
    text_en = text_field("Depoimento", "EN")
    text_pt = text_field("Depoimento", "PT")
    text_es = text_field("Depoimento", "ES")
    source = models.CharField("origem", max_length=80, blank=True,
                              help_text="Onde a avaliação foi feita, ex.: Google, Tripadvisor, e-mail.")
    review_date = models.DateField("data da avaliação", null=True, blank=True)
    active = models.BooleanField("publicado", default=True)
    order = models.PositiveIntegerField("ordem", default=0)
    confirmed_real = models.BooleanField(
        "confirmo que é uma avaliação real", default=False,
        help_text="Somente avaliações reais confirmadas são exibidas no site.")
    booking = models.OneToOneField("bookings.BookingRequest", verbose_name="reserva", on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="review")
    from_customer = models.BooleanField(
        "enviada pelo cliente", default=False,
        help_text="Escrita pelo próprio cliente no link de avaliação (texto não pode ser alterado pela equipe).")
    language = models.CharField("idioma", max_length=8, blank=True)

    objects = TestimonialQuerySet.as_manager()

    text = Localized(fallback=False)  # never show a review in another language

    class Meta:
        verbose_name = "depoimento"
        verbose_name_plural = "depoimentos"
        ordering = ["order", "-review_date", "-created_at"]
        indexes = [models.Index(fields=["active", "order"])]

    def __str__(self):
        return self.author_name

    @property
    def any_text(self):
        """The review in the language it was written (reviews are never machine-translated)."""
        preferred = {"pt-br": self.text_pt, "en": self.text_en, "es": self.text_es}.get(self.language)
        return preferred or self.text_pt or self.text_en or self.text_es

    @property
    def stars(self):
        return range(self.rating or 0)

    def clean(self):
        if not (self.text_en or self.text_pt or self.text_es):
            raise ValidationError("Informe o texto do depoimento em pelo menos um idioma.")


class ContactMessage(TimeStampedModel):
    name = models.CharField("nome", max_length=120)
    email = models.EmailField("e-mail")
    phone = models.CharField("telefone / WhatsApp", max_length=40, blank=True)
    language = models.CharField("idioma", max_length=8, default="en")
    subject = models.CharField("assunto", max_length=150, blank=True)
    message = models.TextField("mensagem")
    consent_at = models.DateTimeField("consentimento LGPD em", null=True, blank=True)
    handled = models.BooleanField("respondida", default=False)
    internal_notes = models.TextField("observações internas", blank=True)

    class Meta:
        verbose_name = "mensagem de contato"
        verbose_name_plural = "mensagens de contato"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.created_at:%d/%m/%Y %H:%M}" if self.created_at else self.name


__all__ = ["SiteSettings", "Testimonial", "ContactMessage", "TimeStampedModel", "lines"]
