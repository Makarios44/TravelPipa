"""
Transfer texts: the 10% deposit is paid by Pix when the booking is confirmed (no more
"we contact you about the deposit"), and Ponta Negra has no round-trip discount for now.
Only text still exactly as loaded is replaced; panel edits are kept.
"""
from django.db import migrations

FIELDS = ("description", "important_info", "meta_description")
SUFFIXES = ("pt", "en", "es")

CHANGES = {
    "natal-airport-pipa-transfer": [
        ("de chegada; depois entramos em contato com os detalhes do embarque e o sinal de 10% que garante a sua reserva.",
         "de chegada. Ao confirmar, você paga o sinal de 10% por Pix e entramos em contato o mais rápido possível com os detalhes do embarque."),
        ("book; we then contact you with the pickup details and the 10% deposit that secures your booking.",
         "book. When you confirm you pay the 10% deposit by Pix, and we contact you as soon as possible with the pickup details."),
        ("reservar; después te contactamos con los detalles de la recogida y la seña del 10% que garantiza tu reserva.",
         "reservar. Al confirmar pagas la seña del 10% con Pix y te contactamos lo antes posible con los detalles de la recogida."),
    ],
    "pipa-ponta-negra-natal-transfer": [
        ("Negociamos desconto fechando ida e volta. Depois da reserva, entramos em contato com o horário de saída e o "
         "sinal de 10% que garante a sua reserva.",
         "Ao confirmar a reserva, você paga o sinal de 10% por Pix; depois entramos em contato o mais rápido possível "
         "para alinhar o horário de saída e os detalhes."),
        ("We negotiate a discount for round trips. After you book, we contact you with the departure time and the 10% "
         "deposit that secures your booking.",
         "When you confirm the booking you pay the 10% deposit by Pix; then we contact you as soon as possible to "
         "arrange the departure time and the details."),
        ("Negociamos un descuento si cierras ida y vuelta. Después de la reserva, te contactamos con el horario de "
         "salida y la seña del 10% que garantiza tu reserva.",
         "Al confirmar la reserva pagas la seña del 10% con Pix; después te contactamos lo antes posible para acordar "
         "el horario de salida y los detalles."),
        ("Negociamos desconto fechando ida e volta\n", ""),
        ("We negotiate a discount for round trips\n", ""),
        ("Negociamos un descuento si cierras ida y vuelta\n", ""),
        ("(até 3 pessoas). Negociamos desconto na ida e volta.", "(até 3 pessoas). Reserve com sinal de 10% por Pix."),
        ("(up to 3 people). Negotiable round-trip discount.", "(up to 3 people). Book with a 10% deposit by Pix."),
        ("(hasta 3 personas). Descuento negociable en ida y vuelta.",
         "(hasta 3 personas). Reserva con una seña del 10% con Pix."),
    ],
}


def forwards(apps, schema_editor):
    Experience = apps.get_model("tours", "Experience")
    for slug, changes in CHANGES.items():
        exp = Experience.objects.filter(slug=slug).first()
        if not exp:
            continue
        changed = []
        for base in FIELDS:
            for suffix in SUFFIXES:
                field = f"{base}_{suffix}"
                value = getattr(exp, field, None) or ""
                new = value
                for old, replacement in changes:
                    new = new.replace(old, replacement)
                if new != value:
                    setattr(exp, field, new)
                    changed.append(field)
        if changed:
            exp.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("tours", "0016_ponta_negra_and_speedboat_prices")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
