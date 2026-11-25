"""
Airport transfer gets its price table (Nov 2026):

    up to 3 people  R$ 240 one way · R$ 230 per leg on a round trip
    4 people        R$ 280 · R$ 270
    5 people        R$ 300 · R$ 290
    6 people        2 cars (3 + 3) — cheaper than a van
    7 or more       group: the team sends a quote

The table is only filled in if it is still empty, and the texts below are only
replaced where they still hold exactly the sentence loaded by the site, so
anything edited in the panel is left as it is.
"""
from django.db import migrations

from tours.price_table_wording import GROUP_FROM, RATES, SLUG, apply

FIELDS = [f"{base}_{lang}" for base in ("summary", "description", "important_info", "meta_description")
          for lang in ("pt", "en", "es")]


def forwards(apps, schema_editor):
    Experience = apps.get_model("tours", "Experience")
    exp = Experience.objects.filter(slug=SLUG).first()
    if exp is None:
        return
    changed = []
    if not exp.transfer_rates.strip():
        exp.transfer_rates = RATES
        changed.append("transfer_rates")
    if exp.group_from is None:
        exp.group_from = GROUP_FROM
        changed.append("group_from")
    for name in FIELDS:
        old = getattr(exp, name) or ""
        new = apply(old)
        if new != old:
            setattr(exp, name, new)
            changed.append(name)
    if changed:
        exp.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("tours", "0009_transfer_price_table")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
