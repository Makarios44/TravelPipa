from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.i18n import Localized, lines
from core.models import IMAGE_VALIDATORS, TimeStampedModel, char_field, text_field
from core.images import optimize_image_field


VIDEO_MAX_MB = 50


def validate_video_size(file):
    if file and file.size > VIDEO_MAX_MB * 1024 * 1024:
        raise ValidationError(f"O vídeo deve ter no máximo {VIDEO_MAX_MB} MB.")


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(active=True)


class Category(TimeStampedModel):
    name_en = char_field("Nome", "EN", 100, blank=False)
    name_pt = char_field("Nome", "PT", 100)
    name_es = char_field("Nome", "ES", 100)
    description_en = text_field("Descrição", "EN")
    description_pt = text_field("Descrição", "PT")
    description_es = text_field("Descrição", "ES")
    slug = models.SlugField("slug (URL)", max_length=80, unique=True, blank=True,
                            help_text="Identificador na URL. Deixe vazio para gerar a partir do nome em inglês.")
    image = models.ImageField("imagem", upload_to="categories/", blank=True, validators=IMAGE_VALIDATORS)
    icon = models.CharField("ícone (Bootstrap Icons)", max_length=40, blank=True,
                            help_text="Opcional, ex.: water, compass, tree, people, car-front.")
    is_transfer = models.BooleanField(
        "é categoria de transfers", default=False,
        help_text="Experiências desta categoria aparecem na página Transfers.")
    order = models.PositiveIntegerField("ordem de exibição", default=0)
    active = models.BooleanField("ativa", default=True)

    objects = ActiveQuerySet.as_manager()

    name = Localized()
    description = Localized()

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        ordering = ["order", "name_en"]
        indexes = [models.Index(fields=["active", "order"])]

    def __str__(self):
        return self.name_pt or self.name_en

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name_en)[:80]
        optimize_image_field(self.image)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('tours:experience_list')}?category={self.slug}"


class ExperienceQuerySet(models.QuerySet):
    def published(self):
        return (self.filter(active=True, category__active=True)
                .select_related("category")
                .prefetch_related("images"))

    def tours(self):
        return self.published().filter(category__is_transfer=False)

    def transfers(self):
        return self.published().filter(category__is_transfer=True)


class Experience(TimeStampedModel):
    class PriceUnit(models.TextChoices):
        PERSON = "person", _("per person")
        GROUP = "group", _("per group")
        VEHICLE = "vehicle", _("per vehicle")

    class TransferType(models.TextChoices):
        PRIVATE = "private", _("Private")
        SHARED = "shared", _("Shared")

    category = models.ForeignKey(Category, verbose_name="categoria", on_delete=models.PROTECT,
                                 related_name="experiences")
    slug = models.SlugField("slug (URL)", max_length=120, unique=True, blank=True,
                            help_text="Deixe vazio para gerar a partir do título em inglês. Ex.: dolphin-bay-boat-tour")

    # --- Localised content -------------------------------------------------
    title_en = char_field("Título", "EN", 150, blank=False)
    title_pt = char_field("Título", "PT", 150)
    title_es = char_field("Título", "ES", 150)
    summary_en = char_field("Resumo curto (cartões)", "EN", 220)
    summary_pt = char_field("Resumo curto (cartões)", "PT", 220)
    summary_es = char_field("Resumo curto (cartões)", "ES", 220)
    description_en = text_field("Descrição", "EN", help_text="Parágrafos separados por linha em branco.")
    description_pt = text_field("Descrição", "PT")
    description_es = text_field("Descrição", "ES")
    duration_en = char_field("Duração", "EN", 80, help_text="Ex.: Approx. 4 hours / Full day")
    duration_pt = char_field("Duração", "PT", 80)
    duration_es = char_field("Duração", "ES", 80)
    itinerary_en = text_field("Itinerário", "EN", help_text="Uma etapa por linha.")
    itinerary_pt = text_field("Itinerário", "PT")
    itinerary_es = text_field("Itinerário", "ES")
    included_en = text_field("O que está incluído", "EN", help_text="Um item por linha.")
    included_pt = text_field("O que está incluído", "PT")
    included_es = text_field("O que está incluído", "ES")
    not_included_en = text_field("O que não está incluído", "EN", help_text="Um item por linha.")
    not_included_pt = text_field("O que não está incluído", "PT")
    not_included_es = text_field("O que não está incluído", "ES")
    important_info_en = text_field("Informações importantes", "EN", help_text="Um item por linha.")
    important_info_pt = text_field("Informações importantes", "PT")
    important_info_es = text_field("Informações importantes", "ES")
    cancellation_policy_en = text_field("Política de cancelamento", "EN",
                                        help_text="Vazio = usa a política padrão das configurações.")
    cancellation_policy_pt = text_field("Política de cancelamento", "PT")
    cancellation_policy_es = text_field("Política de cancelamento", "ES")
    meta_title_en = char_field("Meta title (SEO)", "EN", 70)
    meta_title_pt = char_field("Meta title (SEO)", "PT", 70)
    meta_title_es = char_field("Meta title (SEO)", "ES", 70)
    meta_description_en = char_field("Meta description (SEO)", "EN", 170)
    meta_description_pt = char_field("Meta description (SEO)", "PT", 170)
    meta_description_es = char_field("Meta description (SEO)", "ES", 170)

    # --- Commercial ------------------------------------------------------
    price = models.DecimalField("preço", max_digits=10, decimal_places=2, null=True, blank=True,
                                validators=[MinValueValidator(0)],
                                help_text="Vazio = exibe “preço sob consulta”.")
    currency = models.CharField("moeda", max_length=3, default="BRL",
                                choices=[("BRL", "BRL — Real"), ("USD", "USD — Dólar"), ("EUR", "EUR — Euro")])
    price_unit = models.CharField("preço por", max_length=10, choices=PriceUnit.choices,
                                  default=PriceUnit.PERSON)
    price_is_starting = models.BooleanField("exibir como “a partir de”", default=True)

    # --- Transfer details (only for transfer categories) ------------------
    origin_en = char_field("Origem", "EN", 120)
    origin_pt = char_field("Origem", "PT", 120)
    origin_es = char_field("Origem", "ES", 120)
    destination_en = char_field("Destino", "EN", 120)
    destination_pt = char_field("Destino", "PT", 120)
    destination_es = char_field("Destino", "ES", 120)
    transfer_type = models.CharField("modalidade", max_length=10, choices=TransferType.choices, blank=True)
    max_passengers = models.PositiveSmallIntegerField("capacidade de passageiros", null=True, blank=True)
    transfer_rates = models.TextField(
        "tabela de preços por pessoas", blank=True,
        help_text="Uma linha por tamanho de carro — pessoas: só ida / ida e volta (por trecho). "
                  "Ex.: “3: 240 / 230” = até 3 pessoas, R$ 240 só ida ou R$ 230 cada trecho na ida e volta. "
                  "Acima do maior carro o site sugere 2 carros. Vazio = usa só o preço acima.")
    group_from = models.PositiveSmallIntegerField(
        "grupo a partir de (pessoas)", null=True, blank=True, validators=[MinValueValidator(2)],
        help_text="A partir desta quantidade o site não mostra preço: a equipe entra em contato. Ex.: 7")

    # --- Video (optional) ------------------------------------------------
    video = models.FileField(
        "vídeo", upload_to="experiences/videos/", blank=True,
        validators=[FileExtensionValidator(["mp4", "webm"]), validate_video_size],
        help_text="Opcional. MP4, até 50 MB. Vídeos curtos (até 1 minuto) carregam mais rápido no celular.")
    video_poster = models.ImageField(
        "capa do vídeo", upload_to="experiences/videos/", blank=True, validators=IMAGE_VALIDATORS,
        help_text="Imagem exibida antes de o vídeo começar.")

    # --- Display ---------------------------------------------------------
    cadastur_guide = models.BooleanField(
        "acompanhado por guia com Cadastur", default=False,
        help_text="Mostra o selo de guia com Cadastur perto do botão de reserva.")
    tide_dependent = models.BooleanField(
        "depende da maré baixa", default=False,
        help_text="Mostra na página do passeio os próximos horários de maré baixa (ex.: piscinas naturais).")
    featured = models.BooleanField("destaque", default=False,
                                   help_text="Aparece na página inicial e no topo do catálogo.")
    order = models.PositiveIntegerField("ordem de exibição", default=0)
    active = models.BooleanField("ativa (visível no site)", default=True)
    is_demo = models.BooleanField("conteúdo de demonstração", default=False,
                                  help_text="Marca o item como exemplo no site. Desmarque ao usar dados reais.")

    objects = ExperienceQuerySet.as_manager()

    title = Localized()
    summary = Localized()
    description = Localized()
    duration = Localized()
    itinerary = Localized()
    included = Localized()
    not_included = Localized()
    important_info = Localized()
    cancellation_policy = Localized()
    meta_title = Localized()
    meta_description = Localized()
    origin = Localized()
    destination = Localized()

    class Meta:
        verbose_name = "experiência / passeio"
        verbose_name_plural = "experiências / passeios"
        ordering = ["-featured", "order", "title_en"]
        indexes = [
            models.Index(fields=["active", "featured", "order"]),
            models.Index(fields=["category", "active"]),
        ]

    def __str__(self):
        return self.title_pt or self.title_en

    def clean(self):
        if self.category_id and self.category.is_transfer:
            if not (self.origin_en and self.destination_en):
                raise ValidationError("Para transfers, informe a origem e o destino (pelo menos em inglês).")
        if self.transfer_rates.strip():
            from .transfer_pricing import parse_rates
            try:
                rates = parse_rates(self.transfer_rates)
            except ValidationError as exc:
                raise ValidationError({"transfer_rates": exc.messages})
            if self.group_from and rates and self.group_from <= rates[0].max_people:
                raise ValidationError({"group_from": "O grupo precisa começar acima da menor faixa da tabela."})

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title_en)[:110] or "experience"
            slug, n = base, 2
            while Experience.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        optimize_image_field(self.video_poster)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("tours:experience_detail", kwargs={"slug": self.slug})

    # --- Presentation helpers --------------------------------------------
    @property
    def is_transfer(self):
        return self.category.is_transfer

    @property
    def rates(self):
        """Parsed price table (empty when unset or, defensively, when the text is invalid)."""
        if not hasattr(self, "_rates_cache"):
            from .transfer_pricing import parse_rates
            try:
                self._rates_cache = parse_rates(self.transfer_rates) if self.is_transfer else []
            except ValidationError:
                self._rates_cache = []
        return self._rates_cache

    @property
    def price_rows(self):
        """Rows for the public price table: one per car size, then 2 cars, then group."""
        from .transfer_pricing import quote
        rates = self.rates
        if not rates:
            return []
        rows, start = [], 1
        for rate in rates:
            rows.append({"from": start, "to": rate.max_people, "cars": 1,
                         "one_way": rate.one_way, "round_leg": rate.round_leg})
            start = rate.max_people + 1
        last = (self.group_from - 1) if self.group_from else start - 1
        for people in range(start, last + 1):
            two = quote(self, people, False)
            if two and two.kind == "two_cars":
                rt = quote(self, people, True)
                rows.append({"from": people, "to": people, "cars": 2, "split": two.cars,
                             "one_way": two.per_leg, "round_leg": rt.per_leg})
        return rows

    @property
    def description_paragraphs(self):
        return [p.strip() for p in (self.description or "").split("\n\n") if p.strip()]

    @property
    def itinerary_list(self):
        return lines(self.itinerary)

    @property
    def included_list(self):
        return lines(self.included)

    @property
    def not_included_list(self):
        return lines(self.not_included)

    @property
    def important_info_list(self):
        return lines(self.important_info)

    @property
    def gallery(self):
        # Main photos only (the "inside the vehicle" album has its own section).
        # Uses the prefetched relation (ordered in ExperienceImage.Meta).
        return [img for img in self.images.all() if not img.album]

    @property
    def inside_gallery(self):
        return [img for img in self.images.all() if img.album == ExperienceImage.Album.INSIDE]

    @property
    def cover(self):
        images = self.gallery
        for img in images:
            if img.is_cover:
                return img
        return images[0] if images else None


class ExperienceImage(TimeStampedModel):
    experience = models.ForeignKey(Experience, verbose_name="experiência", on_delete=models.CASCADE,
                                   related_name="images")
    image = models.ImageField("imagem", upload_to="experiences/%Y/%m/", validators=IMAGE_VALIDATORS,
                              width_field="width", height_field="height")
    width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    alt_en = char_field("Texto alternativo", "EN", 160, help_text="Descreva a foto (acessibilidade e SEO).")
    alt_pt = char_field("Texto alternativo", "PT", 160)
    alt_es = char_field("Texto alternativo", "ES", 160)
    is_cover = models.BooleanField("capa", default=False)
    order = models.PositiveIntegerField("ordem", default=0)

    class Album(models.TextChoices):
        MAIN = "", "Galeria principal"
        INSIDE = "inside", "Por dentro do veículo"

    album = models.CharField(
        "álbum", max_length=20, choices=Album.choices, blank=True, default=Album.MAIN,
        help_text="“Por dentro do veículo” aparece numa seção própria da página, abaixo da descrição.")

    alt = Localized()

    class Meta:
        verbose_name = "imagem"
        verbose_name_plural = "imagens"
        ordering = ["-is_cover", "order", "id"]

    def __str__(self):
        return self.image.name.rsplit("/", 1)[-1]

    def save(self, *args, **kwargs):
        if self.album:  # the cover always comes from the main gallery
            self.is_cover = False
        optimize_image_field(self.image)
        super().save(*args, **kwargs)
        if self.is_cover:
            ExperienceImage.objects.filter(experience=self.experience, is_cover=True).exclude(pk=self.pk).update(
                is_cover=False)

    @property
    def alt_text(self):
        return self.alt or self.experience.title
