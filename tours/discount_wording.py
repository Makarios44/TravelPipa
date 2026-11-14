"""Round-trip wording: the discount is negotiated, not automatic (Nov 2026)."""

REPLACEMENTS = [
    # Portuguese
    (", com desconto na ida e volta.", "."),
    ("Fechando ida e volta, você ganha um desconto especial.", "Negociamos desconto fechando ida e volta."),
    ("Desconto especial fechando ida e volta", "Negociamos desconto fechando ida e volta"),
    ("Desconto na ida e volta e carros de 7 lugares para grupos.",
     "Carros de 7 lugares para grupos e desconto negociado na ida e volta."),
    ("(até 3 pessoas). Desconto na ida e volta.", "(até 3 pessoas). Negociamos desconto na ida e volta."),
    # English
    (", with a round-trip discount.", "."),
    ("Book the round trip and get a special discount.", "We negotiate a discount for round trips."),
    ("Special discount for round trips", "We negotiate a discount for round trips"),
    ("Round-trip discount and 7-seat cars for groups.", "7-seat cars for groups and a negotiable round-trip discount."),
    ("(up to 3 people). Round-trip discount.", "(up to 3 people). Negotiable round-trip discount."),
    # Spanish
    (", con descuento en ida y vuelta.", "."),
    ("Reservando ida y vuelta tienes un descuento especial.", "Negociamos un descuento si cierras ida y vuelta."),
    ("Descuento especial en ida y vuelta", "Negociamos un descuento si cierras ida y vuelta"),
    ("Descuento en ida y vuelta y coches de 7 plazas para grupos.",
     "Coches de 7 plazas para grupos y descuento negociable en ida y vuelta."),
    ("(hasta 3 personas). Descuento en ida y vuelta.", "(hasta 3 personas). Descuento negociable en ida y vuelta."),
]


def apply(text):
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text
