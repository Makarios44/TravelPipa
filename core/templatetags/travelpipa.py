from decimal import Decimal

from django import template
from django.utils.translation import get_language, gettext as _

register = template.Library()

CURRENCY_SYMBOLS = {"BRL": "R$", "USD": "US$", "EUR": "€"}


def format_number(value, lang):
    value = Decimal(value)
    decimals = 0 if value == value.to_integral() else 2
    text = f"{value:,.{decimals}f}"
    if lang in ("pt-br", "es"):
        text = text.replace(",", "§").replace(".", ",").replace("§", ".")
    return text


@register.filter
def money(value, currency="BRL"):
    if value in (None, ""):
        return ""
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    return f"{symbol} {format_number(value, get_language())}"


@register.inclusion_tag("includes/price.html")
def price_block(experience, compact=False):
    unit_labels = {
        "person": _("per person"),
        "group": _("per group"),
        "vehicle": _("per vehicle"),
    }
    return {
        "has_price": experience.price is not None,
        "amount": money(experience.price, experience.currency) if experience.price is not None else "",
        "starting": experience.price_is_starting,
        "unit": unit_labels.get(experience.price_unit, ""),
        "compact": compact,
        "is_demo": experience.is_demo,
    }


@register.simple_tag
def lang_url(code, path):
    """Language switch URL that remembers the choice in a cookie."""
    from urllib.parse import urlencode

    from django.urls import reverse

    return reverse("switch_language", args=[code]) + "?" + urlencode({"next": path})


@register.filter
def initials(name):
    parts = [p for p in (name or "").split() if p]
    return "".join(p[0] for p in parts[:2]).upper()
