"""
Updates transfers already on the site:
* round-trip discount is now "negotiated" (not automatic);
* the airport transfer gets its price (R$ 240 per car, up to 3 people) if it still has none.
Only exact old sentences are replaced, so texts edited in the panel are kept.
"""
from decimal import Decimal

from django.db import migrations

SLUGS = ["natal-airport-pipa-transfer", "pipa-ponta-negra-natal-transfer"]
FIELDS = ["summary", "description", "important_info", "meta_description"]
SUFFIXES = ["pt", "en", "es"]


def forwards(apps, schema_editor):
    from tours.discount_wording import apply

    Experience = apps.get_model("tours", "Experience")
    for exp in Experience.objects.filter(slug__in=SLUGS):
        changed = []
        for base in FIELDS:
            for suffix in SUFFIXES:
                name = f"{base}_{suffix}"
                old = getattr(exp, name, "") or ""
                new = apply(old)
                limit = Experience._meta.get_field(name).max_length
                if limit:
                    new = new[:limit]
                if new != old:
                    setattr(exp, name, new)
                    changed.append(name)
        if exp.slug == "natal-airport-pipa-transfer" and exp.price is None:
            exp.price = Decimal("240.00")
            exp.price_unit = "vehicle"
            exp.price_is_starting = True
            exp.max_passengers = exp.max_passengers or 3
            exp.transfer_type = exp.transfer_type or "private"
            changed += ["price", "price_unit", "price_is_starting", "max_passengers", "transfer_type"]
        if changed:
            exp.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("tours", "0006_experience_cadastur_guide")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
