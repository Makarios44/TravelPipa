"""
Prices set by the team (27/11/2026):
* Transfer Pipa ⇄ Ponta Negra/Natal: R$ 210 per car (up to 3 people); bigger groups on request.
  With the price table, bookings get the 10% deposit link automatically.
* Speedboat tour (Baía dos Golfinhos): R$ 70 per person, fixed price (not "from").
"""
from django.db import migrations

PONTA_NEGRA = "pipa-ponta-negra-natal-transfer"
SPEEDBOAT = "pipa-dolphin-bay-speedboat-tour"
TEXT_FIELDS = ("title", "summary", "description", "duration", "itinerary", "included", "not_included",
               "important_info", "meta_title", "meta_description")
OLD_NEW = (("a partir de R$ 230", "a partir de R$ 210"), ("from R$ 230", "from R$ 210"),
           ("desde R$ 230", "desde R$ 210"), ("R$ 230", "R$ 210"))


def forwards(apps, schema_editor):
    Experience = apps.get_model("tours", "Experience")
    exp = Experience.objects.filter(slug=PONTA_NEGRA).first()
    if exp:
        exp.price = 210
        if not (exp.transfer_rates or "").strip():
            exp.transfer_rates, exp.group_from = "3: 210", 4
        for base in TEXT_FIELDS:
            for suffix in ("pt", "en", "es"):
                field = f"{base}_{suffix}"
                value = getattr(exp, field, None)
                if value:
                    for old, new in OLD_NEW:
                        value = value.replace(old, new)
                    setattr(exp, field, value)
        exp.save()
    Experience.objects.filter(slug=SPEEDBOAT).update(price=70, price_unit="person", price_is_starting=False)


class Migration(migrations.Migration):
    dependencies = [("tours", "0015_people_per_vehicle")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
