import datetime

from django import forms
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _

from core.antispam import AntiSpamFormMixin
from core.forms import ConsentField, StyledFormMixin
from tours.models import Experience

from .models import BookingRequest


class ExperienceSelect(forms.Select):
    """Marks transfer options so the form can show the one-way / round-trip choice."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        instance = getattr(value, "instance", None)
        if instance is not None and instance.is_transfer:
            option["attrs"]["data-transfer"] = "1"
        return option


class ExperienceChoiceField(forms.ModelChoiceField):
    widget = ExperienceSelect

    def label_from_instance(self, obj):
        return obj.title


TRIP_ONE_WAY = "one_way"
TRIP_ROUND = "round_trip"


class BookingRequestForm(StyledFormMixin, AntiSpamFormMixin):
    experience = ExperienceChoiceField(
        label=_("Experience or transfer"), queryset=Experience.objects.none(),
        empty_label=_("Select an option"),
        error_messages={"invalid_choice": _("Please choose an available experience.")},
    )
    preferred_date = forms.DateField(label=_("Date"), widget=forms.DateInput(attrs={"type": "date"}))
    trip_type = forms.ChoiceField(
        label=_("Trip"), required=False, initial=TRIP_ONE_WAY, widget=forms.RadioSelect,
        choices=[(TRIP_ONE_WAY, _("One way")), (TRIP_ROUND, _("Round trip"))])
    return_date = forms.DateField(label=_("Return date"), required=False,
                                  widget=forms.DateInput(attrs={"type": "date"}))
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
        self.fields["return_date"].widget.attrs["min"] = today.isoformat()
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

    def clean(self):
        cleaned = super().clean()
        experience = cleaned.get("experience")
        is_round = (cleaned.get("trip_type") == TRIP_ROUND and experience is not None and experience.is_transfer)
        cleaned["round_trip"] = is_round
        if not is_round:
            cleaned["return_date"] = None
        else:
            back, going = cleaned.get("return_date"), cleaned.get("preferred_date")
            if not back:
                self.add_error("return_date", _("Please choose the date of the return trip."))
            elif going and back < going:
                self.add_error("return_date", _("The return date must be on or after the outbound date."))
        return cleaned

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
            round_trip=data.get("round_trip", False),
            return_date=data.get("return_date"),
            people=data["people"],
            full_name=data["full_name"].strip(),
            email=data["email"],
            phone=data["phone"],
            service_language=data["service_language"],
            site_language=get_language() or "",
            notes=data.get("notes", ""),
            consent_at=timezone.now(),
        )
