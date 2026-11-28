"""Forms for the TravelPipa management panel."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from bookings.models import BookingRequest
from core.i18n import SUFFIXES
from core.images import ALLOWED_EXTENSIONS, MAX_UPLOAD_MB, optimize_image_field
from core.models import SiteSettings, Testimonial
from tours.models import Category, Experience, ExperienceImage

LANG_TABS = [("pt", "Português"), ("en", "Inglês"), ("es", "Espanhol")]


def style_widgets(form):
    """Bootstrap classes for every widget (switches for checkboxes)."""
    for name, field in form.fields.items():
        widget = field.widget
        if isinstance(widget, forms.HiddenInput):
            continue
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "form-check-input")
            widget.attrs.setdefault("role", "switch")
        elif isinstance(widget, forms.Select):
            widget.attrs.setdefault("class", "form-select")
        elif isinstance(widget, forms.FileInput):
            widget.attrs.setdefault("class", "form-control")
        else:
            widget.attrs.setdefault("class", "form-control")
        if isinstance(widget, forms.Textarea):
            widget.attrs.setdefault("rows", 4)
    for name in form.errors:
        if name in form.fields:
            widget = form.fields[name].widget
            widget.attrs["class"] = widget.attrs.get("class", "") + " is-invalid"


class PanelFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_widgets(self)

    def full_clean(self):
        super().full_clean()
        style_widgets(self)

    def fields_named(self, names):
        return [self[name] for name in names if name in self.fields]

    def lang_fields(self, bases, suffix):
        return self.fields_named([f"{base}_{suffix}" for base in bases])


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
class PanelLoginForm(PanelFormMixin, AuthenticationForm):
    error_messages = {
        "invalid_login": "Usuário ou senha incorretos.",
        "inactive": "Este usuário está desativado.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuário"
        self.fields["password"].label = "Senha"
        self.fields["username"].widget.attrs.update({"autocomplete": "username", "autofocus": True})

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError("Este usuário não tem acesso ao painel.", code="no_access")


class PanelPasswordChangeForm(PanelFormMixin, PasswordChangeForm):
    pass


# --------------------------------------------------------------------------
# Experiences
# --------------------------------------------------------------------------
EXPERIENCE_TEXT_BASES = ["title", "summary", "description", "duration", "itinerary", "included",
                         "not_included", "important_info", "cancellation_policy"]
EXPERIENCE_SEO_BASES = ["meta_title", "meta_description"]
EXPERIENCE_STATUS = ["active", "featured", "tide_dependent", "cadastur_guide", "is_demo"]


class ExperienceForm(PanelFormMixin, forms.ModelForm):
    class Meta:
        model = Experience
        fields = (
            ["category", "slug", "order"] + EXPERIENCE_STATUS
            + ["price", "currency", "price_unit", "price_is_starting"]
            + [f"{b}_{s}" for b in EXPERIENCE_TEXT_BASES + EXPERIENCE_SEO_BASES for s in SUFFIXES]
            + [f"{b}_{s}" for b in ("origin", "destination") for s in SUFFIXES]
            + ["transfer_type", "max_passengers", "transfer_rates", "group_from", "video", "video_poster"]
        )
        widgets = {
            **{f"{b}_{s}": forms.Textarea(attrs={"rows": 6 if b == "description" else 4})
               for b in ("description", "itinerary", "included", "not_included", "important_info",
                         "cancellation_policy") for s in SUFFIXES},
            "transfer_rates": forms.Textarea(attrs={"rows": 4, "placeholder": "3: 240 / 230\n4: 280 / 270\n5: 300 / 290",
                                                    "class": "font-monospace"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.order_by("order", "name_pt")
        self.fields["category"].label_from_instance = lambda c: c.name_pt or c.name_en
        self.fields["slug"].required = False

    def text_tabs(self):
        return [
            {"code": code, "label": label, "fields": self.lang_fields(EXPERIENCE_TEXT_BASES, code),
             "seo": self.lang_fields(EXPERIENCE_SEO_BASES, code),
             "transfer": self.lang_fields(["origin", "destination"], code)}
            for code, label in LANG_TABS
        ]


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """Several images in one field (pattern from the Django documentation)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={
            "accept": ",".join(f".{ext}" for ext in ALLOWED_EXTENSIONS), "class": "form-control"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        files = data if isinstance(data, (list, tuple)) else [data]
        files = [f for f in files if f]
        if not files:
            raise forms.ValidationError("Selecione pelo menos uma foto.")
        cleaned = []
        for upload in files:
            ext = upload.name.rsplit(".", 1)[-1].lower() if "." in upload.name else ""
            if ext not in ALLOWED_EXTENSIONS:
                raise forms.ValidationError(f"“{upload.name}”: use fotos JPG, PNG ou WEBP.")
            if upload.size > MAX_UPLOAD_MB * 1024 * 1024:
                raise forms.ValidationError(f"“{upload.name}”: a foto deve ter no máximo {MAX_UPLOAD_MB} MB.")
            cleaned.append(single(upload, initial))
        return cleaned


class PhotoUploadForm(forms.Form):
    photos = MultipleImageField(label="Fotos")


class PhotoAltForm(PanelFormMixin, forms.ModelForm):
    class Meta:
        model = ExperienceImage
        fields = ["album", "alt_pt", "alt_en", "alt_es"]
        labels = {"album": "Álbum", "alt_pt": "Descrição (PT)", "alt_en": "Descrição (EN)",
                  "alt_es": "Descrição (ES)"}


# --------------------------------------------------------------------------
# Categories / testimonials / bookings / settings
# --------------------------------------------------------------------------
class CategoryForm(PanelFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name_pt", "name_en", "name_es", "description_pt", "description_en", "description_es",
                  "slug", "icon", "image", "is_transfer", "order", "active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False


class TestimonialForm(PanelFormMixin, forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ["author_name", "author_country", "experience", "rating", "source", "review_date",
                  "text_pt", "text_en", "text_es", "confirmed_real", "active", "order"]
        widgets = {"review_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["experience"].queryset = Experience.objects.order_by("title_pt", "title_en")
        self.fields["experience"].label_from_instance = lambda e: e.title_pt or e.title_en
        if self.instance.pk and self.instance.from_customer:
            # The customer's own words, rating and name are never edited by the team.
            for name in ("author_name", "rating", "text_pt", "text_en", "text_es", "source", "review_date",
                         "confirmed_real"):
                self.fields[name].disabled = True
                self.fields[name].help_text = "Escrito pelo cliente: não pode ser alterado."


class BookingUpdateForm(PanelFormMixin, forms.ModelForm):
    class Meta:
        model = BookingRequest
        fields = ["status", "deposit_amount", "internal_notes"]
        widgets = {"internal_notes": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [(value, label.split(" (")[0])
                                         for value, label in BookingRequest.Status.choices]
        self.fields["deposit_amount"].label = "Valor do sinal (R$)"
        self.fields["deposit_amount"].help_text = (
            "O cliente paga este valor por Pix pelo Mercado Pago. Vazio = sem cobrança online.")
        if self.instance.payment_status == BookingRequest.PaymentStatus.PAID:
            self.fields["deposit_amount"].disabled = True
            self.fields["deposit_amount"].help_text = "Sinal já pago: não pode ser alterado."

    def clean_deposit_amount(self):
        value = self.cleaned_data.get("deposit_amount")
        if value is not None and value < 1:
            raise forms.ValidationError("Use pelo menos R$ 1,00 ou deixe vazio.")
        return value

    def save(self, commit=True):
        booking = super().save(commit=False)
        if "deposit_amount" in self.changed_data:
            # The old Mercado Pago link carries the old amount: a new one is created on the next visit.
            booking.mp_preference_id = ""
            booking.mp_init_point = ""
            if booking.payment_status == BookingRequest.PaymentStatus.WAITING:
                booking.payment_status = BookingRequest.PaymentStatus.NONE
        if commit:
            booking.save()
        return booking


class VoucherForm(PanelFormMixin, forms.ModelForm):
    """Trip details and amounts printed on the customer and driver vouchers."""
    class Meta:
        model = BookingRequest
        fields = ["pickup_time", "pickup_place", "dropoff_place", "flight_number", "return_time",
                  "total_price", "deposit_received"]
        widgets = {"pickup_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
                   "return_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, prefix="vch", **kwargs)
        booking = self.instance
        if booking.total_price is None and booking.quoted_total is not None:
            self.initial["total_price"] = booking.quoted_total
            self.fields["total_price"].help_text = "Sugerido pelo valor calculado na reserva; confira."
        if not booking.round_trip:
            del self.fields["return_time"]
        if booking.payment_status == BookingRequest.PaymentStatus.PAID:
            del self.fields["deposit_received"]

    def clean(self):
        data = super().clean()
        total, deposit = data.get("total_price"), data.get("deposit_received")
        if total is not None and total < 0:
            self.add_error("total_price", "Valor inválido.")
        if deposit is not None and total is not None and deposit > total:
            self.add_error("deposit_received", "O sinal não pode ser maior que o valor total.")
        return data


class DriverForm(PanelFormMixin, forms.ModelForm):
    """Driver and car for one booking; sent to the customer by e-mail or WhatsApp."""
    class Meta:
        model = BookingRequest
        fields = ["driver_name", "vehicle_model", "vehicle_plate", "driver_phone", "vehicle_der",
                  "driver_photo", "vehicle_photo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, prefix="drv", **kwargs)
        for name in ("driver_photo", "vehicle_photo"):
            self.fields[name].widget.attrs["accept"] = "image/*"

    def clean_vehicle_plate(self):
        plate = "".join(self.cleaned_data.get("vehicle_plate", "").split()).upper()
        if plate and not (7 <= len(plate.replace("-", "")) <= 8 and plate.replace("-", "").isalnum()):
            raise forms.ValidationError("Placa inválida. Ex.: TOV8H80 ou ABC-1234.")
        return plate

    def save(self, commit=True):
        booking = super().save(commit=False)
        for name in ("driver_photo", "vehicle_photo"):
            if name in self.changed_data:
                optimize_image_field(getattr(booking, name))
        if commit:
            booking.save()
        return booking


SETTINGS_GROUPS = [
    ("Contato", ["whatsapp", "phone", "email", "address", "google_maps_url"]),
    ("Redes sociais", ["instagram", "facebook", "tiktok", "youtube", "tripadvisor"]),
    ("Imagens do site", ["hero_image", "about_image", "logo", "og_image"]),
    ("Google (avaliações)", ["google_place_id"]),
    ("Selos de confiança", ["trust_cadastur_guides", "trust_der_vehicles"]),
    ("Dados da empresa (aparecem no rodapé)", ["site_name", "company_legal_name", "company_document", "cadastur"]),
]
SETTINGS_TEXT_BASES = ["opening_hours", "about_intro", "about_body", "pipa_region", "default_cancellation"]
SETTINGS_LEGAL_BASES = ["privacy_policy", "terms"]


class SiteSettingsForm(PanelFormMixin, forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ([name for _, names in SETTINGS_GROUPS for name in names]
                  + [f"{b}_{s}" for b in SETTINGS_TEXT_BASES + SETTINGS_LEGAL_BASES for s in SUFFIXES])
        widgets = {f"{b}_{s}": forms.Textarea(attrs={"rows": 8 if b in ("about_body", "privacy_policy", "terms") else 4})
                   for b in SETTINGS_TEXT_BASES[1:] + SETTINGS_LEGAL_BASES for s in SUFFIXES}

    def groups(self):
        return [(title, self.fields_named(names)) for title, names in SETTINGS_GROUPS]

    def text_tabs(self):
        return [{"code": code, "label": label, "fields": self.lang_fields(SETTINGS_TEXT_BASES, code),
                 "legal": self.lang_fields(SETTINGS_LEGAL_BASES, code)} for code, label in LANG_TABS]
