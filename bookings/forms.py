import datetime

from django import forms
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _

from core.antispam import AntiSpamFormMixin
from core.forms import ConsentField, StyledFormMixin
from tours.models import Experience

from .models import BookingRequest


class ExperienceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.title


class BookingRequestForm(StyledFormMixin, AntiSpamFormMixin):
    experience = ExperienceChoiceField(
        label=_("Experience or transfer"), queryset=Experience.objects.none(),
        empty_label=_("Select an option"),
        error_messages={"invalid_choice": _("Please choose an available experience.")},
    )
    preferred_date = forms.DateField(label=_("Preferred date"), widget=forms.DateInput(attrs={"type": "date"}))
    people = forms.IntegerField(label=_("Number of people"), min_value=1, max_value=60, initial=2,
                                widget=forms.NumberInput(attrs={"inputmode": "numeric"}))
    full_name = forms.CharField(label=_("Full name"), max_length=150,
                                widget=forms.TextInput(attrs={"autocomplete": "name"}))
    email = forms.EmailField(label=_("E-mail"), widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    phone = forms.CharField(label=_("WhatsApp or phone"), max_length=40,
                            help_text=_("Include the country code, e.g. +1 555 123 4567."),
                            widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}))
    service_language = forms.ChoiceField(label=_("Preferred language for our contact"),
                                         choices=BookingRequest.Language.choices)
    notes = forms.CharField(label=_("Additional notes (optional)"), required=False, max_length=2000,
                            widget=forms.Textarea(attrs={"rows": 4}),
                            help_text=_("Hotel or pickup area, flight number for transfers, children's ages, special needs…"))
    consent = ConsentField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["experience"].queryset = Experience.objects.published().order_by(
            "category__is_transfer", "category__order", "order", "title_en")
        today = timezone.localdate()
        self.fields["preferred_date"].widget.attrs["min"] = today.isoformat()
        self.fields["preferred_date"].widget.attrs["max"] = (today + datetime.timedelta(days=730)).isoformat()
        if not self.is_bound:
            lang = get_language()
            self.initial.setdefault("service_language", lang if lang in dict(BookingRequest.Language.choices) else "en")
        self.apply_styles()

    def clean_preferred_date(self):
        value = self.cleaned_data["preferred_date"]
        today = timezone.localdate()
        if value < today:
            raise forms.ValidationError(_("Please choose a date from today onwards."))
        if value > today + datetime.timedelta(days=730):
            raise forms.ValidationError(_("Please choose a date within the next two years."))
        return value

    def clean_phone(self):
        value = self.cleaned_data["phone"].strip()
        digits = "".join(ch for ch in value if ch.isdigit())
        if not 8 <= len(digits) <= 15:
            raise forms.ValidationError(_("Please enter a valid phone number with country code."))
        return value

    def save(self):
        data = self.cleaned_data
        return BookingRequest.objects.create(
            experience=data["experience"],
            experience_title=data["experience"].title_en,
            preferred_date=data["preferred_date"],
            people=data["people"],
            full_name=data["full_name"].strip(),
            email=data["email"],
            phone=data["phone"],
            service_language=data["service_language"],
            site_language=get_language() or "",
            notes=data.get("notes", ""),
            consent_at=timezone.now(),
        )
