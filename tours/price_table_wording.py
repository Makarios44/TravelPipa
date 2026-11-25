"""Airport transfer wording once it has a price table (Nov 2026): prices live in the
table on the page, the texts only explain it. Used by migration 0010 and load_tours."""

SLUG = "natal-airport-pipa-transfer"
RATES = "3: 240 / 230\n4: 280 / 270\n5: 300 / 290"
GROUP_FROM = 7

REPLACEMENTS = [
    # Portuguese
    ("O valor é por carro, para até 3 pessoas. Para famílias e grupos maiores, temos carros de 7 lugares "
     "e opções para grupos grandes: informe quantas pessoas viajam e indicamos a melhor opção.",
     "O valor é por carro e depende do número de pessoas (veja a tabela de preços). Para 6 pessoas indicamos "
     "2 carros, que sai mais barato que alugar uma van; para grupos a partir de 7 pessoas, a nossa equipe "
     "envia o orçamento."),
    ("Negociamos desconto fechando ida e volta. Reserve", "Fechando ida e volta, cada trecho sai mais barato. Reserve"),
    ("Carro com motorista entre o Aeroporto de Natal e Pipa. Valor por carro, para até 3 pessoas.",
     "Carro com motorista entre o Aeroporto de Natal e Pipa. Valor por carro, mais barato na ida e volta."),
    ("Valor por carro, para até 3 pessoas\n", "Valor por carro, conforme o número de pessoas (veja a tabela)\n"),
    ("Carros de 7 lugares e grupos grandes: valor sob consulta",
     "6 pessoas: 2 carros, mais barato que uma van · 7 ou mais: valor sob consulta"),
    ("Negociamos desconto fechando ida e volta", "Ida e volta: cada trecho sai mais barato"),
    ("Carros de 7 lugares e desconto negociado na ida e volta.", "Carros de 7 lugares e desconto na ida e volta."),
    # English
    ("The price is per car, for up to 3 people. For families and larger groups we have 7-seat cars and options "
     "for large groups: tell us how many people are travelling and we suggest the best option.",
     "The price is per car and depends on the number of people (see the price table). For 6 people we suggest "
     "2 cars, which is cheaper than renting a van; for groups of 7 or more, our team sends you a quote."),
    ("We negotiate a discount for round trips. Include", "Book the round trip and each leg costs less. Include"),
    ("Car with driver between Natal Airport and Pipa. Price per car for up to 3 people.",
     "Car with driver between Natal Airport and Pipa. Price per car, lower on round trips."),
    ("Price per car, for up to 3 people\n", "Price per car, by number of people (see the table)\n"),
    ("7-seat cars and large groups: price on request",
     "6 people: 2 cars, cheaper than a van · 7 or more: price on request"),
    ("We negotiate a discount for round trips", "Round trip: each leg costs less"),
    ("7-seat cars for groups and a negotiable round-trip discount.", "7-seat cars for groups and a round-trip discount."),
    # Spanish
    ("El precio es por coche, para hasta 3 personas. Para familias y grupos más grandes tenemos coches de 7 plazas "
     "y opciones para grupos grandes: cuéntanos cuántas personas viajan y te indicamos la mejor opción.",
     "El precio es por coche y depende del número de personas (mira la tabla de precios). Para 6 personas "
     "sugerimos 2 coches, que sale más barato que alquilar una van; para grupos de 7 o más, nuestro equipo te "
     "envía el presupuesto."),
    ("Negociamos un descuento si cierras ida y vuelta. Indica", "Reservando ida y vuelta, cada trayecto sale más barato. Indica"),
    ("Coche con conductor entre el Aeropuerto de Natal y Pipa. Precio por coche, hasta 3 personas.",
     "Coche con conductor entre el Aeropuerto de Natal y Pipa. Precio por coche, más barato en ida y vuelta."),
    ("Precio por coche, para hasta 3 personas\n", "Precio por coche, según el número de personas (mira la tabla)\n"),
    ("Coches de 7 plazas y grupos grandes: precio a consultar",
     "6 personas: 2 coches, más barato que una van · 7 o más: precio a consultar"),
    ("Negociamos un descuento si cierras ida y vuelta", "Ida y vuelta: cada trayecto sale más barato"),
    ("Coches de 7 plazas para grupos y descuento negociable en ida y vuelta.",
     "Coches de 7 plazas para grupos y descuento en ida y vuelta."),
]


def apply(text):
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text
