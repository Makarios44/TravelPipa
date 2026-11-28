"""
Transfer photos on the live site: the BYD (partner vehicle registered with DER/RN)
becomes the cover, its interior photos move to the "Por dentro do veículo" album,
and texts claiming our own vehicles are DER/RN-registered now say we work with
registered partners. Only photos loaded by the seed (matched by file name) and
texts still exactly as loaded are touched; panel edits are kept.
"""
from pathlib import Path

from django.db import migrations

ORDER = {
    "natal-airport-pipa-transfer": (
        ["08-byd-traseira", "03-spin-7-lugares-frente", "07-spin-lateral", "09-spin-7-lugares",
         "05-spin-terceira-fileira", "02-sedan-transfer", "01-carro-eletrico-mirante"],
        ["04-byd-interior-painel", "06-byd-banco-traseiro"],
    ),
    "pipa-ponta-negra-natal-transfer": (
        ["08-byd-traseira", "03-spin-7-lugares-frente", "01-carro-eletrico-mirante"],
        ["06-byd-banco-traseiro"],
    ),
}

ALT = {  # 07-spin-lateral: the Spin is not the DER/RN-registered car
    "alt_pt": ("Lateral do carro de 7 lugares, com selo de transporte turístico do DER/RN",
               "Lateral do carro de 7 lugares (Chevrolet Spin) usado nos transfers"),
    "alt_en": ("Side of the 7-seat car, with the DER/RN tourist transport sticker",
               "Side of the 7-seat car (Chevrolet Spin) used for transfers"),
    "alt_es": ("Lateral del coche de 7 plazas, con el sello de transporte turístico del DER/RN",
               "Lateral del coche de 7 plazas (Chevrolet Spin) usado en los traslados"),
}

INFO = {
    "important_info_pt": ("Veículos cadastrados para transporte turístico no DER/RN",
                          "Transporte feito por parceiros cadastrados no DER/RN para transporte turístico"),
    "important_info_en": ("Vehicles registered for tourist transport with DER/RN (Rio Grande do Norte transport authority)",
                          "Transport by partners registered with DER/RN (Rio Grande do Norte transport authority) for tourist transport"),
    "important_info_es": ("Vehículos registrados para transporte turístico en el DER/RN (órgano de transporte de Rio Grande do Norte)",
                          "Transporte a cargo de socios registrados en el DER/RN (órgano de transporte de Rio Grande do Norte) para transporte turístico"),
}


def _seed_stem(name, stems):
    stem = Path(name).stem
    return next((s for s in stems if stem == s or stem.startswith(s + "_")), None)


def forwards(apps, schema_editor):
    Experience = apps.get_model("tours", "Experience")
    ExperienceImage = apps.get_model("tours", "ExperienceImage")

    for exp in Experience.objects.all():
        changed = []
        for field, (old, new) in INFO.items():
            value = getattr(exp, field, None) or ""
            lines = value.split("\n")
            if old in lines:
                setattr(exp, field, "\n".join(new if l == old else l for l in lines))
                changed.append(field)
        if changed:
            exp.save(update_fields=changed)

    for slug, (main, inside) in ORDER.items():
        exp = Experience.objects.filter(slug=slug).first()
        if not exp:
            continue
        images = list(ExperienceImage.objects.filter(experience=exp))
        by_stem = {}
        for img in images:
            stem = _seed_stem(img.image.name, main + inside)
            if stem and stem not in by_stem:
                by_stem[stem] = img
        if "08-byd-traseira" not in by_stem:
            continue  # BYD photo not on the site: leave this experience as the team arranged it
        extras = [img for img in images if img not in by_stem.values()]
        position = 0
        for stem in main:
            img = by_stem.get(stem)
            if img:
                img.order, img.album, img.is_cover = position, "", stem == "08-byd-traseira"
                position += 1
        for img in sorted(extras, key=lambda i: (i.order, i.id)):  # photos uploaded in the panel
            if not img.album:
                img.order, img.is_cover = position, False
                position += 1
        for stem in inside:
            img = by_stem.get(stem)
            if img:
                img.order, img.album, img.is_cover = position, "inside", False
                position += 1
        for img in images:
            if _seed_stem(img.image.name, ["07-spin-lateral"]):
                for field, (old, new) in ALT.items():
                    if getattr(img, field) == old:
                        setattr(img, field, new)
            img.save()


class Migration(migrations.Migration):
    dependencies = [("tours", "0011_image_album")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
