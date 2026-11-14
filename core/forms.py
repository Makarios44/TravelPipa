from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .antispam import AntiSpamFormMixin


class StyledFormMixin:
    """Adds Bootstrap classes and accessibility attributes to every widget."""

    def apply_styles(self):
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.HiddenInput):
                continue
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")
            if field.required:
                widget.attrs.setdefault("required", True)
                widget.attrs["aria-required"] = "true"

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                attrs = self.fields[name].widget.attrs
                if "is-invalid" not in attrs.get("class", ""):
                    attrs["class"] = attrs.get("class", "") + " is-invalid"
                attrs["aria-invalid"] = "true"
                attrs["aria-describedby"] = f"id_{name}_error"


class ConsentField(forms.BooleanField):
    def __init__(self, **kwargs):
        super().__init__(
            required=True,
            label=_("I agree that TravelPipa may use my data to answer this request, as described in the Privacy Policy."),
            error_messages={"required": _("Please accept the privacy terms so we can answer you.")},
            **kwargs,
        )


class ContactForm(StyledFormMixin, AntiSpamFormMixin):
    name = forms.CharField(label=_("Full name"), max_length=120,
                           widget=forms.TextInput(attrs={"autocomplete": "name"}))
    email = forms.EmailField(label=_("E-mail"), widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    phone = forms.CharField(label=_("WhatsApp or phone (optional)"), max_length=40, required=False,
                            widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}))
    subject = forms.CharField(label=_("Subject"), max_length=150, required=False)
    message = forms.CharField(label=_("Message"), max_length=3000,
                              widget=forms.Textarea(attrs={"rows": 5}))
    consent = ConsentField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()

    def save(self, language):
        from .models import ContactMessage

        data = self.cleaned_data
        return ContactMessage.objects.create(
            name=data["name"], email=data["email"], phone=data.get("phone", ""),
            subject=data.get("subject", ""), message=data["message"], language=language,
            consent_at=timezone.now(),
        )
