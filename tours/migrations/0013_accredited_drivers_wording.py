"""
Transfers: "important information" now says we work with a network of accredited
partner drivers (DER/RN) and that car and driver are confirmed up to 12 hours
before the trip, with photos. Only lines still exactly as loaded are replaced.
"""
from django.db import migrations

INFO = {
    "important_info_pt": (
        ["Veículos cadastrados para transporte turístico no DER/RN",
         "Transporte feito por parceiros cadastrados no DER/RN para transporte turístico"],
        ["Transporte feito pela nossa rede de motoristas parceiros credenciados no DER/RN para transporte turístico",
         "Carro e motorista confirmados até 12 horas antes da viagem, com foto do carro e do motorista"],
    ),
    "important_info_en": (
        ["Vehicles registered for tourist transport with DER/RN (Rio Grande do Norte transport authority)",
         "Transport by partners registered with DER/RN (Rio Grande do Norte transport authority) for tourist transport"],
        ["Transport by our network of accredited partner drivers, registered with DER/RN (Rio Grande do Norte "
         "transport authority) for tourist transport",
         "Car and driver confirmed up to 12 hours before the trip, with a photo of the car and the driver"],
    ),
    "important_info_es": (
        ["Vehículos registrados para transporte turístico en el DER/RN (órgano de transporte de Rio Grande do Norte)",
         "Transporte a cargo de socios registrados en el DER/RN (órgano de transporte de Rio Grande do Norte) "
         "para transporte turístico"],
        ["Transporte a cargo de nuestra red de conductores asociados acreditados en el DER/RN (órgano de transporte "
         "de Rio Grande do Norte) para transporte turístico",
         "Coche y conductor confirmados hasta 12 horas antes del viaje, con foto del coche y del conductor"],
    ),
}


def new_text(value, old_lines, new_lines):
    lines = (value or "").split("\n")
    if not any(line in old_lines for line in lines):
        return None
    out = []
    for line in lines:
        if line in old_lines:
            out.extend(l for l in new_lines if l not in out and l not in lines)
        else:
            out.append(line)
    return "\n".join(out)


def forwards(apps, schema_editor):
    Experience = apps.get_model("tours", "Experience")
    for exp in Experience.objects.all():
        changed = []
        for field, (old_lines, new_lines) in INFO.items():
            text = new_text(getattr(exp, field, ""), old_lines, new_lines)
            if text is not None:
                setattr(exp, field, text)
                changed.append(field)
        if changed:
            exp.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("tours", "0012_byd_cover_and_inside_album")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
