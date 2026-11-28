"""
Loads TravelPipa's real experiences (texts in EN / PT / ES).

Safe to run again: experiences are updated by slug, photos and settings
changed in the admin panel are kept.

    python manage.py load_tours
"""
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import SiteSettings
from tours.models import Category, Experience, ExperienceImage
from tours import price_table_wording

# Photos and videos supplied by TravelPipa live in this folder (kept in the repository).
CONTENT_DIR = Path(settings.BASE_DIR) / "content"

# Site-wide images (SiteSettings field -> file in CONTENT_DIR)
SITE_IMAGES = {
    "hero_image": "photos/site/pipa-panorama-por-do-sol.jpg",  # home page banner
    "about_image": "photos/site/pipa-mare-baixa-por-do-sol.jpg",  # "Cliffs, warm sea..." section
}

CATEGORIES = {
    "boat-experiences": dict(name_en="Boat Experiences", name_pt="Passeios de barco",
                             name_es="Paseos en barco", icon="water", order=1),
    "adventure-tours": dict(name_en="Adventure Tours", name_pt="Aventura", name_es="Aventura",
                            icon="compass", order=2),
    "local-experiences": dict(name_en="Local Experiences", name_pt="Experiências locais",
                              name_es="Experiencias locales", icon="people", order=4),
    "transfers": dict(name_en="Transfers", name_pt="Transfers", name_es="Traslados",
                      icon="car-front", is_transfer=True, order=5),
}

# Rules shared by both quad bike routes
QUAD_RULES_PT = (
    "Até 2 pessoas por quadriciclo; o veículo suporta até 220 kg\n"
    "O piloto deve ser maior de idade\n"
    "Idade mínima na garupa: 7 anos\n"
    "Não é permitida a participação de gestantes\n"
    "Não é permitido levar cooler ou aparelho de som\n"
    "O piloto não pode ter consumido nem consumir bebida alcoólica durante o passeio"
)
QUAD_RULES_EN = (
    "Up to 2 people per quad bike; maximum load 220 kg\n"
    "The driver must be 18 or older\n"
    "Minimum age for the passenger: 7 years\n"
    "Not allowed for pregnant women\n"
    "Coolers and sound systems are not allowed\n"
    "The driver must not have drunk alcohol before or during the tour"
)
QUAD_RULES_ES = (
    "Hasta 2 personas por cuatriciclo; el vehículo soporta hasta 220 kg\n"
    "El conductor debe ser mayor de edad\n"
    "Edad mínima para el acompañante: 7 años\n"
    "No se permite la participación de embarazadas\n"
    "No se permite llevar heladera portátil ni equipos de sonido\n"
    "El conductor no puede haber consumido ni consumir alcohol durante el paseo"
)

TOURS = [
    {
        "slug": "natal-airport-pipa-transfer",
        "category": "transfers",
        "featured": True,
        "order": 0,
        "price": Decimal("240.00"),
        "price_unit": "vehicle",
        "price_is_starting": True,  # up to 3 people; bigger cars cost more
        "transfer_type": "private",
        "max_passengers": 3,
        "media": {
            "photos": [
                ("photos/transfer/08-byd-traseira.jpg",
                 "SUV BYD Song Pro usado nos transfers",
                 "BYD Song Pro SUV used for transfers",
                 "SUV BYD Song Pro usado en los traslados"),
                ("photos/transfer/03-spin-7-lugares-frente.jpg",
                 "Carro de 7 lugares (Chevrolet Spin) usado nos transfers",
                 "7-seat car (Chevrolet Spin) used for transfers",
                 "Coche de 7 plazas (Chevrolet Spin) usado en los traslados"),
                ("photos/transfer/07-spin-lateral.jpg",
                 "Lateral do carro de 7 lugares (Chevrolet Spin) usado nos transfers",
                 "Side of the 7-seat car (Chevrolet Spin) used for transfers",
                 "Lateral del coche de 7 plazas (Chevrolet Spin) usado en los traslados"),
                ("photos/transfer/09-spin-7-lugares.jpg",
                 "Carro de 7 lugares estacionado, pronto para o transfer",
                 "7-seat car parked and ready for the transfer",
                 "Coche de 7 plazas estacionado, listo para el traslado"),
                ("photos/transfer/05-spin-terceira-fileira.jpg",
                 "Porta-malas do carro de 7 lugares, com a terceira fileira de bancos",
                 "Boot of the 7-seat car, with the third row of seats",
                 "Maletero del coche de 7 plazas, con la tercera fila de asientos"),
                ("photos/transfer/02-sedan-transfer.jpg",
                 "Sedã branco usado nos transfers",
                 "White sedan used for transfers",
                 "Sedán blanco usado en los traslados"),
                ("photos/transfer/01-carro-eletrico-mirante.jpg",
                 "Carro do transfer em um mirante à beira-mar, com arco-íris ao fundo",
                 "Transfer car at a seaside viewpoint, with a rainbow behind",
                 "Coche del traslado en un mirador junto al mar, con un arcoíris al fondo"),
                ("photos/transfer/04-byd-interior-painel.jpg",
                 "Interior do SUV BYD, com painel e bancos de couro",
                 "Inside the BYD SUV: dashboard and leather seats",
                 "Interior del SUV BYD, con tablero y asientos de cuero",
                 "inside"),
                ("photos/transfer/06-byd-banco-traseiro.jpg",
                 "Banco traseiro de couro do SUV BYD",
                 "Leather rear seat of the BYD SUV",
                 "Asiento trasero de cuero del SUV BYD",
                 "inside"),
            ],
        },
        "pt": {
            "title": "Transfer Aeroporto de Natal ↔ Pipa",
            "summary": "Carro com motorista entre o Aeroporto de Natal e Pipa. Valor por carro, para até 3 pessoas.",
            "description": (
                "Comece e termine a viagem sem preocupação: um carro com motorista leva você do Aeroporto "
                "Internacional de Natal até a sua hospedagem em Pipa, ou faz o caminho de volta.\n\n"
                "O valor é por carro, para até 3 pessoas. Para famílias e grupos maiores, temos carros de 7 lugares "
                "e opções para grupos grandes: informe quantas pessoas viajam e indicamos a melhor opção.\n\n"
                "Negociamos desconto fechando ida e volta. Reserve informando o número do voo e o horário "
                "de chegada; depois entramos em contato com os detalhes do embarque e o sinal de 10% que garante a sua reserva."
            ),
            "origin": "Aeroporto Internacional de Natal (NAT)",
            "destination": "Praia da Pipa",
            "duration": "",
            "itinerary": "",
            "included": "Carro com motorista",
            "not_included": "",
            "important_info": (
                "Valor por carro, para até 3 pessoas\n"
                "Carros de 7 lugares e grupos grandes: valor sob consulta\n"
                "Negociamos desconto fechando ida e volta\n"
                "Transporte feito pela nossa rede de motoristas parceiros credenciados no DER/RN para transporte turístico\n"
                "Carro e motorista confirmados até 12 horas antes da viagem, com foto do carro e do motorista\n"
                "Informe o número do voo e o horário de chegada na reserva\n"
                "Informe a quantidade de malas para indicarmos o carro certo"
            ),
            "meta_title": "Transfer Aeroporto de Natal para Pipa",
            "meta_description": "Transfer com motorista entre o Aeroporto de Natal e Pipa a partir de R$ 240 por carro (até 3 pessoas). Carros de 7 lugares e desconto negociado na ida e volta.",
        },
        "en": {
            "title": "Natal Airport ↔ Pipa Transfer",
            "summary": "Car with driver between Natal Airport and Pipa. Price per car for up to 3 people.",
            "description": (
                "Start and end your trip without worries: a car with driver takes you from Natal International "
                "Airport to your accommodation in Pipa, or back again.\n\n"
                "The price is per car, for up to 3 people. For families and larger groups we have 7-seat cars "
                "and options for large groups: tell us how many people are travelling and we suggest the best option.\n\n"
                "We negotiate a discount for round trips. Include your flight number and arrival time when you "
                "book; we then contact you with the pickup details and the 10% deposit that secures your booking."
            ),
            "origin": "Natal International Airport (NAT)",
            "destination": "Praia da Pipa",
            "duration": "",
            "itinerary": "",
            "included": "Car with driver",
            "not_included": "",
            "important_info": (
                "Price per car, for up to 3 people\n"
                "7-seat cars and large groups: price on request\n"
                "We negotiate a discount for round trips\n"
                "Transport by our network of accredited partner drivers, registered with DER/RN (Rio Grande do Norte transport authority) for tourist transport\n"
                "Car and driver confirmed up to 12 hours before the trip, with a photo of the car and the driver\n"
                "Include your flight number and arrival time when you book\n"
                "Tell us how many bags you have so we can suggest the right car"
            ),
            "meta_title": "Natal Airport Transfer to Pipa, Brazil",
            "meta_description": "Natal airport transfer to Pipa with driver from R$ 240 per car (up to 3 people). 7-seat cars for groups and a negotiable round-trip discount.",
        },
        "es": {
            "title": "Traslado Aeropuerto de Natal ↔ Pipa",
            "summary": "Coche con conductor entre el Aeropuerto de Natal y Pipa. Precio por coche, hasta 3 personas.",
            "description": (
                "Empieza y termina tu viaje sin preocupaciones: un coche con conductor te lleva desde el Aeropuerto "
                "Internacional de Natal hasta tu alojamiento en Pipa, o hace el camino de vuelta.\n\n"
                "El precio es por coche, para hasta 3 personas. Para familias y grupos más grandes tenemos coches de "
                "7 plazas y opciones para grupos grandes: cuéntanos cuántas personas viajan y te indicamos la mejor opción.\n\n"
                "Negociamos un descuento si cierras ida y vuelta. Indica tu número de vuelo y la hora de llegada al "
                "reservar; después te contactamos con los detalles de la recogida y la seña del 10% que garantiza tu reserva."
            ),
            "origin": "Aeropuerto Internacional de Natal (NAT)",
            "destination": "Praia da Pipa",
            "duration": "",
            "itinerary": "",
            "included": "Coche con conductor",
            "not_included": "",
            "important_info": (
                "Precio por coche, para hasta 3 personas\n"
                "Coches de 7 plazas y grupos grandes: precio a consultar\n"
                "Negociamos un descuento si cierras ida y vuelta\n"
                "Transporte a cargo de nuestra red de conductores asociados acreditados en el DER/RN (órgano de transporte de Rio Grande do Norte) para transporte turístico\n"
                "Coche y conductor confirmados hasta 12 horas antes del viaje, con foto del coche y del conductor\n"
                "Indica tu número de vuelo y la hora de llegada al reservar\n"
                "Indícanos cuántas maletas llevas para sugerir el coche adecuado"
            ),
            "meta_title": "Traslado del aeropuerto de Natal a Pipa",
            "meta_description": "Traslado del aeropuerto de Natal a Pipa con conductor desde R$ 240 por coche (hasta 3 personas). Coches de 7 plazas para grupos y descuento negociable en ida y vuelta.",
        },
    },
    {
        "slug": "pipa-ponta-negra-natal-transfer",
        "category": "transfers",
        "featured": False,
        "order": 1,
        "price": Decimal("230.00"),
        "price_unit": "vehicle",
        "price_is_starting": True,  # up to 3 people; bigger cars cost more
        "transfer_type": "private",
        "max_passengers": 3,
        "media": {
            "photos": [
                ("photos/transfer/08-byd-traseira.jpg",
                 "SUV BYD Song Pro usado nos transfers",
                 "BYD Song Pro SUV used for transfers",
                 "SUV BYD Song Pro usado en los traslados"),
                ("photos/transfer/03-spin-7-lugares-frente.jpg",
                 "Carro de 7 lugares (Chevrolet Spin) usado nos transfers",
                 "7-seat car (Chevrolet Spin) used for transfers",
                 "Coche de 7 plazas (Chevrolet Spin) usado en los traslados"),
                ("photos/transfer/01-carro-eletrico-mirante.jpg",
                 "Carro do transfer em um mirante à beira-mar, com arco-íris ao fundo",
                 "Transfer car at a seaside viewpoint, with a rainbow behind",
                 "Coche del traslado en un mirador junto al mar, con un arcoíris al fondo"),
                ("photos/transfer/06-byd-banco-traseiro.jpg",
                 "Banco traseiro de couro do SUV BYD",
                 "Leather rear seat of the BYD SUV",
                 "Asiento trasero de cuero del SUV BYD",
                 "inside"),
            ],
        },
        "pt": {
            "title": "Transfer Pipa ↔ Ponta Negra (Natal)",
            "summary": "Carro com motorista entre Pipa e Ponta Negra, a praia mais conhecida de Natal. Valor por carro, para até 3 pessoas.",
            "description": (
                "Vai dividir a viagem entre Pipa e Natal? Um carro com motorista leva você da sua hospedagem em Pipa "
                "até Ponta Negra, o bairro de praia mais conhecido de Natal, aos pés do Morro do Careca, ou faz o "
                "caminho de volta.\n\n"
                "O valor é por carro, para até 3 pessoas. Para famílias e grupos maiores, temos carros de 7 lugares: "
                "informe quantas pessoas viajam e indicamos a melhor opção.\n\n"
                "Negociamos desconto fechando ida e volta. Depois da reserva, entramos em contato com o "
                "horário de saída e o sinal de 10% que garante a sua reserva."
            ),
            "origin": "Praia da Pipa",
            "destination": "Ponta Negra, Natal",
            "duration": "",
            "itinerary": "",
            "included": "Carro com motorista",
            "not_included": "",
            "important_info": (
                "Valor por carro, para até 3 pessoas\n"
                "Carros de 7 lugares e grupos grandes: valor sob consulta\n"
                "Negociamos desconto fechando ida e volta\n"
                "Transporte feito pela nossa rede de motoristas parceiros credenciados no DER/RN para transporte turístico\n"
                "Carro e motorista confirmados até 12 horas antes da viagem, com foto do carro e do motorista\n"
                "Informe os endereços de saída e de chegada na reserva\n"
                "Informe a quantidade de malas para indicarmos o carro certo"
            ),
            "meta_title": "Transfer Pipa para Ponta Negra (Natal)",
            "meta_description": "Transfer com motorista entre Pipa e Ponta Negra, em Natal, a partir de R$ 230 por carro (até 3 pessoas). Negociamos desconto na ida e volta.",
        },
        "en": {
            "title": "Pipa ↔ Ponta Negra (Natal) Transfer",
            "summary": "Car with driver between Pipa and Ponta Negra, Natal's best-known beach. Price per car for up to 3 people.",
            "description": (
                "Splitting your trip between Pipa and Natal? A car with driver takes you from your accommodation in "
                "Pipa to Ponta Negra, Natal's best-known beach district at the foot of Morro do Careca dune, or back "
                "again.\n\n"
                "The price is per car, for up to 3 people. For families and larger groups we have 7-seat cars: tell "
                "us how many people are travelling and we suggest the best option.\n\n"
                "We negotiate a discount for round trips. After you book, we contact you with the departure "
                "time and the 10% deposit that secures your booking."
            ),
            "origin": "Praia da Pipa",
            "destination": "Ponta Negra, Natal",
            "duration": "",
            "itinerary": "",
            "included": "Car with driver",
            "not_included": "",
            "important_info": (
                "Price per car, for up to 3 people\n"
                "7-seat cars and large groups: price on request\n"
                "We negotiate a discount for round trips\n"
                "Transport by our network of accredited partner drivers, registered with DER/RN (Rio Grande do Norte transport authority) for tourist transport\n"
                "Car and driver confirmed up to 12 hours before the trip, with a photo of the car and the driver\n"
                "Include the pickup and drop-off addresses when you book\n"
                "Tell us how many bags you have so we can suggest the right car"
            ),
            "meta_title": "Pipa to Ponta Negra (Natal) Transfer",
            "meta_description": "Transfer with driver between Pipa and Ponta Negra, Natal, from R$ 230 per car (up to 3 people). Negotiable round-trip discount.",
        },
        "es": {
            "title": "Traslado Pipa ↔ Ponta Negra (Natal)",
            "summary": "Coche con conductor entre Pipa y Ponta Negra, la playa más conocida de Natal. Precio por coche, hasta 3 personas.",
            "description": (
                "¿Vas a dividir tu viaje entre Pipa y Natal? Un coche con conductor te lleva desde tu alojamiento en "
                "Pipa hasta Ponta Negra, el barrio de playa más conocido de Natal, al pie del Morro do Careca, o hace "
                "el camino de vuelta.\n\n"
                "El precio es por coche, para hasta 3 personas. Para familias y grupos más grandes tenemos coches de "
                "7 plazas: cuéntanos cuántas personas viajan y te indicamos la mejor opción.\n\n"
                "Negociamos un descuento si cierras ida y vuelta. Después de la reserva, te contactamos con el "
                "horario de salida y la seña del 10% que garantiza tu reserva."
            ),
            "origin": "Praia da Pipa",
            "destination": "Ponta Negra, Natal",
            "duration": "",
            "itinerary": "",
            "included": "Coche con conductor",
            "not_included": "",
            "important_info": (
                "Precio por coche, para hasta 3 personas\n"
                "Coches de 7 plazas y grupos grandes: precio a consultar\n"
                "Negociamos un descuento si cierras ida y vuelta\n"
                "Transporte a cargo de nuestra red de conductores asociados acreditados en el DER/RN (órgano de transporte de Rio Grande do Norte) para transporte turístico\n"
                "Coche y conductor confirmados hasta 12 horas antes del viaje, con foto del coche y del conductor\n"
                "Indica las direcciones de salida y de llegada al reservar\n"
                "Indícanos cuántas maletas llevas para sugerir el coche adecuado"
            ),
            "meta_title": "Traslado de Pipa a Ponta Negra (Natal)",
            "meta_description": "Traslado con conductor entre Pipa y Ponta Negra, en Natal, desde R$ 230 por coche (hasta 3 personas). Descuento negociable en ida y vuelta.",
        },
    },
    {
        "slug": "pipa-dolphin-bay-speedboat-tour",
        "category": "boat-experiences",
        "media": {
            "photos": [
                ("photos/lancha/01-lancha-com-turistas.jpg",
                 "Lancha com turistas de colete salva-vidas no mar de Pipa",
                 "Speedboat with tourists in life jackets on the sea in Pipa",
                 "Lancha con turistas con chaleco salvavidas en el mar de Pipa"),
                ("photos/lancha/02-lancha-ancorada-baia.jpg",
                 "Lancha ancorada em frente à praia, com a Mata Atlântica ao fundo",
                 "Speedboat anchored off the beach, with the Atlantic Forest behind",
                 "Lancha anclada frente a la playa, con la Mata Atlántica al fondo"),
                ("photos/lancha/03-interior-da-lancha.jpg",
                 "Interior da lancha, com bancos estofados e coletes salva-vidas",
                 "Inside the speedboat: padded seats and life jackets",
                 "Interior de la lancha, con asientos acolchados y chalecos salvavidas"),
                ("photos/lancha/04-vista-do-mar.jpg",
                 "Vista do mar de Pipa a bordo da lancha",
                 "View of the sea from the speedboat",
                 "Vista del mar desde la lancha"),
            ],
            "video": "videos/lancha-baia-dos-golfinhos.mp4",
            "video_poster": "videos/lancha-baia-dos-golfinhos-poster.jpg",
        },
        "featured": True,
        "order": 1,
        "price": Decimal("70.00"),
        "price_unit": "person",
        "price_is_starting": True,
        "pt": {
            "title": "Passeio de lancha à Baía dos Golfinhos",
            "summary": "Uma hora pelo mar de Pipa, passando pelas falésias até a Baía dos Golfinhos, com parada para banho.",
            "description": (
                "Pipa fica ainda mais bonita vista do mar. A lancha sai da Praia do Centro e segue junto às falésias, "
                "passando pela Praia do Madeiro e pela Praia do Curral até chegar à grande estrela do passeio: "
                "a Baía dos Golfinhos.\n\n"
                "Lá, a lancha diminui o ritmo para observar os golfinhos e faz uma parada de cerca de 15 minutos "
                "para um banho de mar. Depois, é só voltar curtindo a vista.\n\n"
                "Rápido, leve e inesquecível: em uma hora você conhece três praias do complexo da Pipa."
            ),
            "duration": "50 min a 1 hora",
            "itinerary": (
                "Embarque na Praia do Centro de Pipa\n"
                "Praia do Madeiro\n"
                "Praia do Curral\n"
                "Baía dos Golfinhos: observação dos golfinhos\n"
                "Parada para banho na Baía dos Golfinhos (cerca de 15 minutos)\n"
                "Retorno à Praia do Centro"
            ),
            "included": "Passeio de lancha (coletiva ou privativa)\nParada para banho na Baía dos Golfinhos",
            "not_included": "Taxa de preservação ambiental: R$ 10 por pessoa",
            "important_info": (
                "Lancha coletiva: R$ 70 por pessoa no dinheiro ou Pix, ou R$ 75 no cartão de crédito ou débito\n"
                "Lancha privativa: R$ 1.050 pela lancha\n"
                "A taxa de preservação ambiental (R$ 10 por pessoa) é paga aos fiscais da prefeitura antes do embarque\n"
                "Os golfinhos vivem livres na natureza, por isso o avistamento não pode ser garantido"
            ),
            "meta_title": "Passeio de lancha na Baía dos Golfinhos em Pipa",
            "meta_description": "Passeio de lancha em Pipa: Praia do Madeiro, Praia do Curral e Baía dos Golfinhos, com parada para banho. Lancha coletiva ou privativa.",
        },
        "en": {
            "title": "Speedboat Tour to Dolphin Bay",
            "summary": "One hour on the sea of Pipa, along the cliffs to Dolphin Bay, with a stop for a swim.",
            "description": (
                "Pipa looks even better from the sea. The speedboat leaves from the main beach in the village "
                "centre and follows the cliffs past Madeiro Beach and Curral Beach to the highlight of the trip: "
                "Dolphin Bay (Baía dos Golfinhos).\n\n"
                "In the bay, the boat slows down to watch the dolphins and stops for about 15 minutes so you can "
                "swim. Then it's an easy ride back, enjoying the view.\n\n"
                "Short, easy and unforgettable: in one hour you see three beaches of the Pipa coastline."
            ),
            "duration": "50 min to 1 hour",
            "itinerary": (
                "Boarding at Pipa's central beach (Praia do Centro)\n"
                "Madeiro Beach\n"
                "Curral Beach\n"
                "Dolphin Bay: dolphin watching\n"
                "Swim stop at Dolphin Bay (about 15 minutes)\n"
                "Return to the central beach"
            ),
            "included": "Speedboat ride (shared or private)\nSwim stop at Dolphin Bay",
            "not_included": "Environmental preservation fee: R$ 10 per person",
            "important_info": (
                "Shared boat: R$ 70 per person in cash or Pix, or R$ 75 by credit or debit card\n"
                "Private boat: R$ 1,050 for the whole boat\n"
                "The environmental preservation fee (R$ 10 per person) is paid to the municipal inspectors before boarding\n"
                "Dolphins are wild animals, so sightings cannot be guaranteed"
            ),
            "meta_title": "Dolphin Bay Speedboat Tour in Pipa, Brazil",
            "meta_description": "Pipa boat tour to Madeiro Beach, Curral Beach and Dolphin Bay, with a swim stop. Shared or private speedboat from Pipa's central beach.",
        },
        "es": {
            "title": "Paseo en lancha a la Bahía de los Delfines",
            "summary": "Una hora por el mar de Pipa, junto a los acantilados hasta la Bahía de los Delfines, con parada para nadar.",
            "description": (
                "Pipa es todavía más linda vista desde el mar. La lancha sale de la playa del centro y recorre "
                "los acantilados, pasando por la Praia do Madeiro y la Praia do Curral hasta llegar a la gran "
                "estrella del paseo: la Bahía de los Delfines.\n\n"
                "Allí, la lancha baja el ritmo para observar a los delfines y hace una parada de unos 15 minutos "
                "para darse un baño. Después, solo queda volver disfrutando del paisaje.\n\n"
                "Corto, fácil e inolvidable: en una hora conoces tres playas del litoral de Pipa."
            ),
            "duration": "50 min a 1 hora",
            "itinerary": (
                "Embarque en la playa del centro de Pipa\n"
                "Praia do Madeiro\n"
                "Praia do Curral\n"
                "Bahía de los Delfines: observación de delfines\n"
                "Parada para nadar en la Bahía de los Delfines (unos 15 minutos)\n"
                "Regreso a la playa del centro"
            ),
            "included": "Paseo en lancha (compartida o privada)\nParada para nadar en la Bahía de los Delfines",
            "not_included": "Tasa de preservación ambiental: R$ 10 por persona",
            "important_info": (
                "Lancha compartida: R$ 70 por persona en efectivo o Pix, o R$ 75 con tarjeta de crédito o débito\n"
                "Lancha privada: R$ 1.050 por la lancha\n"
                "La tasa de preservación ambiental (R$ 10 por persona) se paga a los fiscales municipales antes del embarque\n"
                "Los delfines viven en libertad, por eso no se puede garantizar el avistamiento"
            ),
            "meta_title": "Paseo en lancha a la Bahía de los Delfines, Pipa",
            "meta_description": "Tour en lancha en Pipa: Praia do Madeiro, Praia do Curral y Bahía de los Delfines, con parada para nadar. Lancha compartida o privada.",
        },
    },
    {
        "slug": "southern-coast-4x4-jeep-tour",
        "tide_dependent": True,
        "category": "adventure-tours",
        "media": {
            "photos": [
                ("photos/jeep/01-jeep-turistas-falesia.png",
                 "Turistas acenando em um jeep 4x4 no alto da falésia, com o mar ao fundo",
                 "Guests waving from a 4x4 jeep on the cliff top, with the sea behind",
                 "Turistas saludando desde un jeep 4x4 en lo alto del acantilado, con el mar al fondo"),
                ("photos/jeep/02-jeep-mirante-litoral.png",
                 "Jeep 4x4 no alto da falésia, com vista para o litoral",
                 "4x4 jeep on the cliff top overlooking the coast",
                 "Jeep 4x4 en lo alto del acantilado, con vista a la costa"),
                ("photos/jeep/03-banho-piscina-natural.jpg",
                 "Turista se banhando em uma piscina natural entre as pedras",
                 "Guest bathing in a natural rock pool",
                 "Turista bañándose en una piscina natural entre las rocas"),
                ("photos/jeep/04-familia-piscinas-naturais.jpg",
                 "Família nas piscinas naturais da maré baixa",
                 "Family at the natural pools at low tide",
                 "Familia en las piscinas naturales con la marea baja"),
                ("photos/jeep/05-piscina-natural-agua-clara.jpg",
                 "Piscina natural de água transparente entre as pedras",
                 "Natural pool with clear water among the rocks",
                 "Piscina natural de agua transparente entre las rocas"),
            ],
        },
        "featured": True,
        "order": 2,
        "price": Decimal("120.00"),
        "price_unit": "person",
        "price_is_starting": False,
        "pt": {
            "title": "Passeio de jeep 4x4 pelo litoral sul",
            "summary": "Um dia inteiro de falésias, piscinas naturais, travessia de rio, dunas e pôr do sol na Lagoa de Guaraíras.",
            "description": (
                "Das 10h às 18h, o jeep 4x4 leva você aos cenários mais bonitos do litoral, com busca no seu "
                "hotel ou pousada.\n\n"
                "O dia começa no Chapadão, descendo a falésia até a Praia das Minas, área de desova de tartarugas. "
                "Em Sibaúma, tem mirante e piscinas naturais. Depois vem a travessia do Rio Catu e a Barra de "
                "Cunhaú, com praias e uma jacuzzi natural para relaxar.\n\n"
                "Após o almoço, o passeio segue para o lado norte: Praia do Madeiro, skibunda nas dunas de "
                "Cacimbinhas e, para fechar o dia, o pôr do sol na Lagoa de Guaraíras."
            ),
            "duration": "Dia inteiro: das 10h às 18h",
            "itinerary": (
                "Busca no seu local de hospedagem\n"
                "Chapadão e descida da falésia\n"
                "Praia das Minas, área de desova de tartarugas\n"
                "Mirante das tartarugas e piscinas naturais de Sibaúma\n"
                "Travessia do Rio Catu\n"
                "Barra de Cunhaú: praias e jacuzzi natural\n"
                "Parada para almoço: Camarão na Fazenda ou Miramar\n"
                "Praia do Madeiro\n"
                "Skibunda nas dunas de Cacimbinhas\n"
                "Pôr do sol na Lagoa de Guaraíras"
            ),
            "included": (
                "Passeio de jeep 4x4\n"
                "Busca no seu local de hospedagem\n"
                "Skibunda nas dunas de Cacimbinhas\n"
                "Almoçando no Camarão na Fazenda: passeio a cavalo, arco e flecha, caiaque e slackline"
            ),
            "not_included": "",
            "important_info": (
                "Horário: das 10h às 18h\n"
                "Almoço no Camarão na Fazenda ou no Miramar, à sua escolha"
            ),
            "meta_title": "Passeio de jeep 4x4 em Pipa: litoral sul e pôr do sol",
            "meta_description": "Passeio de jeep 4x4 saindo de Pipa: Praia das Minas, piscinas naturais de Sibaúma, Rio Catu, Barra de Cunhaú, skibunda e pôr do sol na Lagoa de Guaraíras.",
        },
        "en": {
            "title": "4x4 Jeep Tour along the Southern Coast",
            "summary": "A full day of cliffs, natural pools, a river crossing, dunes and sunset over Guaraíras Lagoon.",
            "description": (
                "From 10 am to 6 pm, a 4x4 jeep takes you to the most beautiful spots on the coast, with pickup "
                "at your hotel or guesthouse.\n\n"
                "The day starts at Chapadão, driving down the cliff to Praia das Minas, a turtle nesting area. "
                "In Sibaúma there is a viewpoint and natural pools. Then comes the crossing of the Catu River and "
                "Barra de Cunhaú, with beaches and a natural jacuzzi to relax in.\n\n"
                "After lunch, the tour heads north: Madeiro Beach, sand-boarding on the dunes of Cacimbinhas "
                "(skibunda) and, to close the day, sunset over Guaraíras Lagoon."
            ),
            "duration": "Full day: 10 am to 6 pm",
            "itinerary": (
                "Pickup at your accommodation\n"
                "Chapadão and the drive down the cliff\n"
                "Praia das Minas, a turtle nesting area\n"
                "Turtle viewpoint and natural pools of Sibaúma\n"
                "Crossing of the Catu River\n"
                "Barra de Cunhaú: beaches and natural jacuzzi\n"
                "Lunch stop: Camarão na Fazenda or Miramar\n"
                "Madeiro Beach\n"
                "Sand-boarding (skibunda) on the dunes of Cacimbinhas\n"
                "Sunset over Guaraíras Lagoon"
            ),
            "included": (
                "4x4 jeep tour\n"
                "Pickup at your accommodation\n"
                "Sand-boarding (skibunda) on the dunes of Cacimbinhas\n"
                "If you have lunch at Camarão na Fazenda: horse riding, archery, kayaking and slackline"
            ),
            "not_included": "",
            "important_info": (
                "Schedule: 10 am to 6 pm\n"
                "Lunch at Camarão na Fazenda or Miramar, your choice"
            ),
            "meta_title": "4x4 Jeep Tour from Pipa: Southern Coast & Sunset",
            "meta_description": "Pipa adventure tour by 4x4 jeep: Praia das Minas, Sibaúma natural pools, Catu River, Barra de Cunhaú, dune sand-boarding and sunset at Guaraíras Lagoon.",
        },
        "es": {
            "title": "Paseo en jeep 4x4 por el litoral sur",
            "summary": "Un día entero de acantilados, piscinas naturales, cruce de río, dunas y atardecer en la Laguna de Guaraíras.",
            "description": (
                "De 10 a 18 h, el jeep 4x4 te lleva a los paisajes más lindos de la costa, con recogida en tu "
                "hotel o posada.\n\n"
                "El día empieza en el Chapadão, bajando el acantilado hasta la Praia das Minas, zona de desove de "
                "tortugas. En Sibaúma hay un mirador y piscinas naturales. Después viene el cruce del río Catu y "
                "Barra de Cunhaú, con playas y un jacuzzi natural para relajarse.\n\n"
                "Tras el almuerzo, el paseo sigue hacia el norte: Praia do Madeiro, skibunda en las dunas de "
                "Cacimbinhas y, para cerrar el día, el atardecer en la Laguna de Guaraíras."
            ),
            "duration": "Día entero: de 10 a 18 h",
            "itinerary": (
                "Recogida en tu alojamiento\n"
                "Chapadão y bajada del acantilado\n"
                "Praia das Minas, zona de desove de tortugas\n"
                "Mirador de las tortugas y piscinas naturales de Sibaúma\n"
                "Cruce del río Catu\n"
                "Barra de Cunhaú: playas y jacuzzi natural\n"
                "Parada para almorzar: Camarão na Fazenda o Miramar\n"
                "Praia do Madeiro\n"
                "Skibunda en las dunas de Cacimbinhas\n"
                "Atardecer en la Laguna de Guaraíras"
            ),
            "included": (
                "Paseo en jeep 4x4\n"
                "Recogida en tu alojamiento\n"
                "Skibunda en las dunas de Cacimbinhas\n"
                "Si almuerzas en Camarão na Fazenda: paseo a caballo, tiro con arco, kayak y slackline"
            ),
            "not_included": "",
            "important_info": (
                "Horario: de 10 a 18 h\n"
                "Almuerzo en Camarão na Fazenda o en Miramar, a tu elección"
            ),
            "meta_title": "Paseo en jeep 4x4 en Pipa: litoral sur y atardecer",
            "meta_description": "Tour en jeep 4x4 desde Pipa: Praia das Minas, piscinas naturales de Sibaúma, río Catu, Barra de Cunhaú, skibunda en las dunas y atardecer en Guaraíras.",
        },
    },
    {
        "slug": "guarairas-lagoon-gastronomic-boat-tour",
        "category": "local-experiences",
        "media": {
            "photos": [
                ("photos/guarairas/01-catamara-banco-de-areia.jpg",
                 "Catamarã parado em um banco de areia na Lagoa de Guaraíras",
                 "Catamaran stopped at a sandbank on Guaraíras Lagoon",
                 "Catamarán detenido en un banco de arena en la Laguna de Guaraíras"),
                ("photos/guarairas/02-catamara-na-lagoa.jpg",
                 "Catamarã de dois andares na lagoa, com turistas na água",
                 "Two-deck catamaran on the lagoon, with guests in the water",
                 "Catamarán de dos pisos en la laguna, con turistas en el agua"),
            ],
            "video": "videos/rota-gastronomica-guarairas.mp4",
            "video_poster": "videos/rota-gastronomica-guarairas-poster.jpg",
        },
        "featured": True,
        "order": 3,
        "price": Decimal("325.00"),
        "price_unit": "person",
        "price_is_starting": True,
        "pt": {
            "title": "Rota Gastronômica na Lagoa de Guaraíras",
            "summary": "Uma tarde de catamarã pela Lagoa de Guaraíras, com banhos nos bancos de areia, almoço de frutos do mar, open bar e pôr do sol.",
            "description": (
                "Uma tarde inteira navegando pela Lagoa de Guaraíras, em Tibau do Sul, com comida boa, bebida "
                "gelada e o pôr do sol mais famoso da região.\n\n"
                "A Guaraíras é uma grande lagoa de água salobra, cercada por manguezais e dunas, que se encontra "
                "com o mar em Tibau do Sul. O catamarã percorre cerca de 8 km pela lagoa e faz de 4 a 6 paradas nos "
                "bancos de areia, perfeitos para um banho e para relaxar com os pés na água.\n\n"
                "A mesa é farta: petiscos para começar, almoço com peixe e camarão grelhados e open bar de "
                "cerveja, caipirinha, refrigerante e sucos de fruta. O passeio termina depois do pôr do sol "
                "sobre a lagoa."
            ),
            "duration": "Tarde inteira: das 12h até depois do pôr do sol",
            "itinerary": (
                "Busca na sua hospedagem entre Pipa e Tibau do Sul, a partir das 11h15 (opção com transporte)\n"
                "Embarque a partir das 12h, em Tibau do Sul\n"
                "Navegação de cerca de 8 km pela Lagoa de Guaraíras\n"
                "De 4 a 6 paradas para banho nos bancos de areia\n"
                "Petiscos e almoço durante o passeio\n"
                "Pôr do sol na lagoa e retorno"
            ),
            "included": (
                "Passeio de catamarã pela Lagoa de Guaraíras, com paradas para banho\n"
                "Petiscos: espetinhos de frango, queijo coalho e bruschetta\n"
                "Almoço: 2 variedades de peixe; espetinhos de filé de camarão, batatas e mariscos grelhados; salada\n"
                "Open bar de cervejas Brahma Chopp, Amstel e Devassa\n"
                "Caipirinhas de cachaça, vodka ou rum\n"
                "Refrigerantes, água e sucos de várias frutas\n"
                "Transporte (na opção de R$ 350)"
            ),
            "not_included": "Ostra fresca (opcional): R$ 3",
            "important_info": (
                "Com transporte: R$ 350 por pessoa\n"
                "Sem transporte: R$ 325 por pessoa\n"
                "Crianças de 7 a 12 anos pagam meia\n"
                "A busca começa às 11h15 e o horário varia conforme o local de hospedagem\n"
                "Embarque a partir das 12h; retorno após o pôr do sol"
            ),
            "meta_title": "Rota Gastronômica na Lagoa de Guaraíras, Tibau do Sul",
            "meta_description": "Passeio de catamarã pela Lagoa de Guaraíras com paradas nos bancos de areia, almoço de peixe e camarão, open bar e pôr do sol. Saída de Pipa ou Tibau do Sul.",
        },
        "en": {
            "title": "Gastronomic Catamaran Tour on Guaraíras Lagoon",
            "summary": "An afternoon by catamaran on Guaraíras Lagoon, with swims on the sandbanks, a seafood lunch, open bar and sunset.",
            "description": (
                "A whole afternoon sailing on Guaraíras Lagoon in Tibau do Sul, with good food, cold drinks and "
                "the most famous sunset in the region.\n\n"
                "Guaraíras is a large brackish lagoon, surrounded by mangroves and dunes, that meets the sea at "
                "Tibau do Sul. The catamaran covers about 8 km across the lagoon and makes 4 to 6 stops on the "
                "sandbanks, perfect for a swim and for relaxing with your feet in the water.\n\n"
                "There is plenty to eat and drink: snacks to start, a lunch of grilled fish and shrimp, and an "
                "open bar with beer, caipirinhas, soft drinks and fruit juices. The tour ends after sunset over "
                "the lagoon."
            ),
            "duration": "Whole afternoon: from 12 pm until after sunset",
            "itinerary": (
                "Pickup at your accommodation between Pipa and Tibau do Sul, from 11:15 am (option with transport)\n"
                "Boarding from 12 pm in Tibau do Sul\n"
                "About 8 km of sailing on Guaraíras Lagoon\n"
                "4 to 6 swim stops on the sandbanks\n"
                "Snacks and lunch during the tour\n"
                "Sunset on the lagoon and return"
            ),
            "included": (
                "Catamaran tour on Guaraíras Lagoon with swim stops\n"
                "Snacks: chicken skewers, grilled coalho cheese and bruschetta\n"
                "Lunch: 2 kinds of fish; grilled shrimp skewers, potatoes and shellfish; salad\n"
                "Open bar with Brahma Chopp, Amstel and Devassa beers\n"
                "Caipirinhas made with cachaça, vodka or rum\n"
                "Soft drinks, water and juices from a wide variety of fruits\n"
                "Transport (R$ 350 option)"
            ),
            "not_included": "Fresh oysters (optional): R$ 3",
            "important_info": (
                "With transport: R$ 350 per person\n"
                "Without transport: R$ 325 per person\n"
                "Children aged 7 to 12 pay half price\n"
                "Pickups start at 11:15 am; the time depends on where you are staying\n"
                "Boarding from 12 pm; return after sunset"
            ),
            "meta_title": "Guaraíras Lagoon Gastronomic Catamaran Tour, near Pipa",
            "meta_description": "Catamaran tour on Guaraíras Lagoon near Pipa, Brazil: sandbank swim stops, grilled fish and shrimp lunch, open bar and sunset. Pickup in Pipa or Tibau do Sul.",
        },
        "es": {
            "title": "Ruta Gastronómica en la Laguna de Guaraíras",
            "summary": "Una tarde en catamarán por la Laguna de Guaraíras, con baños en los bancos de arena, almuerzo de mariscos, barra libre y atardecer.",
            "description": (
                "Una tarde entera navegando por la Laguna de Guaraíras, en Tibau do Sul, con buena comida, "
                "bebida fría y el atardecer más famoso de la región.\n\n"
                "Guaraíras es una gran laguna de agua salobre, rodeada de manglares y dunas, que se une con el "
                "mar en Tibau do Sul. El catamarán recorre unos 8 km por la laguna y hace de 4 a 6 paradas en los "
                "bancos de arena, ideales para bañarse y relajarse con los pies en el agua.\n\n"
                "La mesa es abundante: picoteo para empezar, almuerzo con pescado y camarones a la parrilla y "
                "barra libre de cerveza, caipiriña, refrescos y jugos de frutas. El paseo termina después del "
                "atardecer sobre la laguna."
            ),
            "duration": "Toda la tarde: desde las 12 h hasta después del atardecer",
            "itinerary": (
                "Recogida en tu alojamiento entre Pipa y Tibau do Sul, desde las 11:15 h (opción con transporte)\n"
                "Embarque desde las 12 h en Tibau do Sul\n"
                "Unos 8 km de navegación por la Laguna de Guaraíras\n"
                "De 4 a 6 paradas para bañarse en los bancos de arena\n"
                "Picoteo y almuerzo durante el paseo\n"
                "Atardecer en la laguna y regreso"
            ),
            "included": (
                "Paseo en catamarán por la Laguna de Guaraíras con paradas para bañarse\n"
                "Picoteo: brochetas de pollo, queso coalho y bruschetta\n"
                "Almuerzo: 2 variedades de pescado; brochetas de camarón, papas y mariscos a la parrilla; ensalada\n"
                "Barra libre de cervezas Brahma Chopp, Amstel y Devassa\n"
                "Caipiriñas de cachaça, vodka o ron\n"
                "Refrescos, agua y jugos de una gran variedad de frutas\n"
                "Transporte (en la opción de R$ 350)"
            ),
            "not_included": "Ostras frescas (opcional): R$ 3",
            "important_info": (
                "Con transporte: R$ 350 por persona\n"
                "Sin transporte: R$ 325 por persona\n"
                "Niños de 7 a 12 años pagan la mitad\n"
                "La recogida empieza a las 11:15 h y el horario depende de dónde te alojes\n"
                "Embarque desde las 12 h; regreso después del atardecer"
            ),
            "meta_title": "Ruta Gastronómica en la Laguna de Guaraíras, Pipa",
            "meta_description": "Paseo en catamarán por la Laguna de Guaraíras cerca de Pipa: baños en bancos de arena, almuerzo de pescado y camarón, barra libre y atardecer.",
        },
    },
    {
        "slug": "quad-bike-tour-route-1",
        "media": {
            "photos": [
                ("photos/quadriciclo/r1-01-casal-acenando.png",
                 "Casal acenando de capacete em um quadriciclo na estrada de terra à beira-mar",
                 "Couple in helmets waving from a quad bike on a dirt road by the sea",
                 "Pareja con casco saludando desde un cuatriciclo en un camino de tierra junto al mar"),
                ("photos/quadriciclo/r12-mirante-falesia.png",
                 "Quadriciclo no alto da falésia, com vista para a praia",
                 "Quad bike on the cliff top, overlooking the beach",
                 "Cuatriciclo en lo alto del acantilado, con vista a la playa"),
                ("photos/quadriciclo/r1-03-grupo-vista-aerea.png",
                 "Vista aérea do grupo de quadriciclos parado no alto da falésia",
                 "Aerial view of the quad bike group stopped on the cliff top",
                 "Vista aérea del grupo de cuatriciclos detenido en lo alto del acantilado"),
                ("photos/quadriciclo/r1-04-comboio-trilha.png",
                 "Comboio de quadriciclos seguindo o guia por uma trilha de terra",
                 "Line of quad bikes following the guide along a dirt track",
                 "Fila de cuatriciclos siguiendo al guía por un camino de tierra"),
                ("photos/quadriciclo/r1-05-quadriciclo-falesia.png",
                 "Quadriciclo à beira da falésia, com coqueiros e mar ao fundo",
                 "Quad bike at the edge of the cliff, with palm trees and sea behind",
                 "Cuatriciclo al borde del acantilado, con cocoteros y mar al fondo"),
            ],
        },
        "cadastur_guide": True,
        "tide_dependent": True,
        "category": "adventure-tours",
        "featured": False,
        "order": 4,
        "price": Decimal("200.00"),
        "price_unit": "vehicle",
        "people_per_vehicle": 2,
        "price_is_starting": False,
        "pt": {
            "title": "Quadriciclo Rota 1: falésias, mirantes e piscinas naturais",
            "summary": "Duas horas de quadriciclo pelo litoral sul de Pipa, com mirantes nas falésias e as piscinas naturais de Sibaúma.",
            "description": (
                "Pilote seu próprio quadriciclo pelas falésias do litoral sul, acompanhado de um guia experiente. "
                "São cerca de 18 km de estrada de terra e paisagens que não se veem da praia.\n\n"
                "A saída é do Restaurante e Tapiocaria Amô. Do Chapadão, você tem a vista da Praia do Amor e segue "
                "pela Praia dos Afogados e pela Praia das Minas até os mirantes do Morro Vermelho e das Tartarugas. "
                "Com a maré baixa, dá para conhecer as piscinas naturais de Sibaúma.\n\n"
                "Na volta, tem parada na fazendinha, com passeio a cavalo, arco e flecha, caiaque e slackline, e "
                "para terminar, day use no Restaurante e Tapiocaria Amô."
            ),
            "duration": "Aprox. 2 horas (cerca de 18 km)",
            "itinerary": (
                "Ponto de encontro: Restaurante e Tapiocaria Amô\n"
                "Chapadão, com vista da Praia do Amor\n"
                "Praia dos Afogados\n"
                "Praia das Minas\n"
                "Mirante do Morro Vermelho\n"
                "Mirante das Tartarugas\n"
                "Piscinas naturais de Sibaúma (com maré baixa)\n"
                "Parada na fazendinha: passeio a cavalo, arco e flecha, caiaque e slackline\n"
                "Day use no Restaurante e Tapiocaria Amô"
            ),
            "included": "Quadriciclo para até 2 pessoas\nGuia experiente acompanhando o passeio",
            "not_included": "Atividades na fazendinha (cavalo, arco e flecha, caiaque e slackline)",
            "important_info": QUAD_RULES_PT,
            "meta_title": "Passeio de quadriciclo em Pipa – Rota 1",
            "meta_description": "Quadriciclo em Pipa: Chapadão, vista da Praia do Amor, Praia das Minas, Morro Vermelho e piscinas naturais de Sibaúma. 2 horas, até 2 pessoas por veículo.",
        },
        "en": {
            "title": "Quad Bike Tour – Route 1: Cliffs, Viewpoints & Natural Pools",
            "summary": "Two hours on a quad bike along the southern coast of Pipa, with cliff-top viewpoints and the natural pools of Sibaúma.",
            "description": (
                "Ride your own quad bike along the cliffs of the southern coast, with an experienced guide. About "
                "18 km of dirt roads and views you can't see from the beach.\n\n"
                "The tour starts at Restaurante e Tapiocaria Amô. From Chapadão you look down on Praia do Amor, then "
                "continue past Praia dos Afogados and Praia das Minas to the Morro Vermelho and Turtle viewpoints. "
                "At low tide you can also visit the natural pools of Sibaúma.\n\n"
                "On the way back there is a stop at a small farm with horse riding, archery, kayaking and "
                "slackline, and the tour ends with day use at Restaurante e Tapiocaria Amô."
            ),
            "duration": "About 2 hours (approx. 18 km)",
            "itinerary": (
                "Meeting point: Restaurante e Tapiocaria Amô\n"
                "Chapadão, with a view over Praia do Amor\n"
                "Praia dos Afogados\n"
                "Praia das Minas\n"
                "Morro Vermelho viewpoint\n"
                "Turtle viewpoint (Mirante das Tartarugas)\n"
                "Natural pools of Sibaúma (at low tide)\n"
                "Farm stop: horse riding, archery, kayaking and slackline\n"
                "Day use at Restaurante e Tapiocaria Amô"
            ),
            "included": "Quad bike for up to 2 people\nExperienced guide throughout the tour",
            "not_included": "Activities at the farm (horse riding, archery, kayaking and slackline)",
            "important_info": QUAD_RULES_EN,
            "meta_title": "Quad Bike Tour in Pipa, Brazil – Route 1",
            "meta_description": "Pipa adventure tour by quad bike: Chapadão, Praia do Amor view, Praia das Minas, Morro Vermelho and Sibaúma natural pools. 2 hours, up to 2 people per quad.",
        },
        "es": {
            "title": "Cuatriciclo Ruta 1: acantilados, miradores y piscinas naturales",
            "summary": "Dos horas en cuatriciclo por el litoral sur de Pipa, con miradores en los acantilados y las piscinas naturales de Sibaúma.",
            "description": (
                "Maneja tu propio cuatriciclo por los acantilados del litoral sur, con un guía experimentado. Son "
                "unos 18 km de caminos de tierra y paisajes que no se ven desde la playa.\n\n"
                "La salida es desde el Restaurante e Tapiocaria Amô. Desde el Chapadão ves la Praia do Amor y sigues "
                "por la Praia dos Afogados y la Praia das Minas hasta los miradores del Morro Vermelho y de las "
                "Tortugas. Con marea baja, también conoces las piscinas naturales de Sibaúma.\n\n"
                "De regreso hay una parada en una granja con paseo a caballo, tiro con arco, kayak y slackline, y "
                "para terminar, day use en el Restaurante e Tapiocaria Amô."
            ),
            "duration": "Aprox. 2 horas (unos 18 km)",
            "itinerary": (
                "Punto de encuentro: Restaurante e Tapiocaria Amô\n"
                "Chapadão, con vista de la Praia do Amor\n"
                "Praia dos Afogados\n"
                "Praia das Minas\n"
                "Mirador del Morro Vermelho\n"
                "Mirador de las Tortugas\n"
                "Piscinas naturales de Sibaúma (con marea baja)\n"
                "Parada en la granja: paseo a caballo, tiro con arco, kayak y slackline\n"
                "Day use en el Restaurante e Tapiocaria Amô"
            ),
            "included": "Cuatriciclo para hasta 2 personas\nGuía experimentado durante todo el paseo",
            "not_included": "Actividades en la granja (caballo, tiro con arco, kayak y slackline)",
            "important_info": QUAD_RULES_ES,
            "meta_title": "Paseo en cuatriciclo en Pipa – Ruta 1",
            "meta_description": "Cuatriciclo en Pipa: Chapadão, vista de la Praia do Amor, Praia das Minas, Morro Vermelho y piscinas naturales de Sibaúma. 2 horas, hasta 2 personas.",
        },
    },
    {
        "slug": "quad-bike-tour-route-2",
        "media": {
            "photos": [
                ("photos/quadriciclo/r12-mirante-falesia.png",
                 "Quadriciclo no alto da falésia, com vista para a praia",
                 "Quad bike on the cliff top, overlooking the beach",
                 "Cuatriciclo en lo alto del acantilado, con vista a la playa"),
                ("photos/quadriciclo/r2-02-dunas-vista-aerea.png",
                 "Vista aérea de quadriciclos nas dunas ao entardecer",
                 "Aerial view of quad bikes on the dunes in the late afternoon",
                 "Vista aérea de cuatriciclos en las dunas al atardecer"),
                ("photos/quadriciclo/r2-03-quadriciclo-e-moto.jpg",
                 "Quadriciclo e moto do guia no alto da falésia, de frente para o mar",
                 "Quad bike and the guide's motorbike on the cliff top, facing the sea",
                 "Cuatriciclo y moto del guía en lo alto del acantilado, frente al mar"),
            ],
        },
        "cadastur_guide": True,
        "tide_dependent": True,
        "category": "adventure-tours",
        "featured": False,
        "order": 5,
        "price": Decimal("300.00"),
        "price_unit": "vehicle",
        "people_per_vehicle": 2,
        "price_is_starting": False,
        "pt": {
            "title": "Quadriciclo Rota 2: Rio Catu, Mata Atlântica e Barra de Cunhaú",
            "summary": "Três horas de quadriciclo com falésias, travessia do Rio Catu, trilhas na Mata Atlântica e o mirante da Barra de Cunhaú.",
            "description": (
                "A rota mais completa de quadriciclo: cerca de 25 km pelo litoral sul, com um guia experiente ao "
                "seu lado do começo ao fim.\n\n"
                "Saindo do Restaurante e Tapiocaria Amô, o caminho passa pelo Chapadão, com parada no mirante da "
                "Praia do Amor, e segue pela Praia das Minas, pelas falésias e pelo Morro Vermelho. Com a maré "
                "baixa, dá para ver as piscinas naturais de Sibaúma. Depois vem a travessia do Rio Catu e trilhas "
                "por estradas rurais, no meio da Mata Atlântica e dos canaviais, até o mirante da Barra de "
                "Cunhaú.\n\n"
                "A volta para Pipa é pelas falésias, com parada para almoço no Restaurante e Tapiocaria Amô."
            ),
            "duration": "Aprox. 3 horas (cerca de 25 km)",
            "itinerary": (
                "Ponto de encontro: Restaurante e Tapiocaria Amô\n"
                "Saída de Pipa em direção ao litoral sul\n"
                "Chapadão, com parada no mirante da Praia do Amor\n"
                "Praia das Minas\n"
                "Falésias e Morro Vermelho\n"
                "Piscinas naturais de Sibaúma (com maré baixa)\n"
                "Travessia do Rio Catu\n"
                "Parada na fazendinha: passeio a cavalo, arco e flecha, caiaque e slackline\n"
                "Trilhas por estradas rurais, entre Mata Atlântica e canaviais\n"
                "Mirante da Barra de Cunhaú\n"
                "Retorno a Pipa pelas falésias\n"
                "Parada para almoço no Restaurante e Tapiocaria Amô"
            ),
            "included": "Quadriciclo para até 2 pessoas\nGuia experiente acompanhando o passeio",
            "not_included": (
                "Atividades na fazendinha (cavalo, arco e flecha, caiaque e slackline)\n"
                "Almoço no Restaurante e Tapiocaria Amô"
            ),
            "important_info": QUAD_RULES_PT,
            "meta_title": "Passeio de quadriciclo em Pipa – Rota 2",
            "meta_description": "Quadriciclo em Pipa: falésias, Morro Vermelho, piscinas de Sibaúma, travessia do Rio Catu, Mata Atlântica e mirante da Barra de Cunhaú. 3 horas.",
        },
        "en": {
            "title": "Quad Bike Tour – Route 2: Catu River, Atlantic Forest & Barra de Cunhaú",
            "summary": "Three hours on a quad bike with cliffs, a Catu River crossing, Atlantic Forest trails and the Barra de Cunhaú viewpoint.",
            "description": (
                "The most complete quad bike route: about 25 km along the southern coast, with an experienced "
                "guide by your side from start to finish.\n\n"
                "Starting from Restaurante e Tapiocaria Amô, the route crosses Chapadão, stopping at the Praia do "
                "Amor viewpoint, and continues along Praia das Minas, the cliffs and Morro Vermelho. At low tide "
                "you can see the natural pools of Sibaúma. Then comes the crossing of the Catu River and trails on "
                "rural roads through Atlantic Forest and sugarcane fields, up to the Barra de Cunhaú viewpoint.\n\n"
                "You return to Pipa along the cliffs, with a lunch stop at Restaurante e Tapiocaria Amô."
            ),
            "duration": "About 3 hours (approx. 25 km)",
            "itinerary": (
                "Meeting point: Restaurante e Tapiocaria Amô\n"
                "Departure from Pipa towards the southern coast\n"
                "Chapadão, with a stop at the Praia do Amor viewpoint\n"
                "Praia das Minas\n"
                "Cliffs and Morro Vermelho\n"
                "Natural pools of Sibaúma (at low tide)\n"
                "Crossing of the Catu River\n"
                "Farm stop: horse riding, archery, kayaking and slackline\n"
                "Trails on rural roads through Atlantic Forest and sugarcane fields\n"
                "Barra de Cunhaú viewpoint\n"
                "Return to Pipa along the cliffs\n"
                "Lunch stop at Restaurante e Tapiocaria Amô"
            ),
            "included": "Quad bike for up to 2 people\nExperienced guide throughout the tour",
            "not_included": (
                "Activities at the farm (horse riding, archery, kayaking and slackline)\n"
                "Lunch at Restaurante e Tapiocaria Amô"
            ),
            "important_info": QUAD_RULES_EN,
            "meta_title": "Quad Bike Tour in Pipa, Brazil – Route 2",
            "meta_description": "Pipa quad bike adventure: cliffs, Morro Vermelho, Sibaúma pools, Catu River crossing, Atlantic Forest trails and Barra de Cunhaú viewpoint. 3 hours.",
        },
        "es": {
            "title": "Cuatriciclo Ruta 2: río Catu, Mata Atlántica y Barra de Cunhaú",
            "summary": "Tres horas en cuatriciclo con acantilados, cruce del río Catu, senderos en la Mata Atlántica y el mirador de Barra de Cunhaú.",
            "description": (
                "La ruta más completa en cuatriciclo: unos 25 km por el litoral sur, con un guía experimentado a tu "
                "lado de principio a fin.\n\n"
                "Saliendo del Restaurante e Tapiocaria Amô, el camino pasa por el Chapadão, con parada en el "
                "mirador de la Praia do Amor, y sigue por la Praia das Minas, los acantilados y el Morro Vermelho. "
                "Con marea baja, se ven las piscinas naturales de Sibaúma. Después viene el cruce del río Catu y "
                "senderos por caminos rurales, entre Mata Atlántica y cañaverales, hasta el mirador de Barra de "
                "Cunhaú.\n\n"
                "El regreso a Pipa es por los acantilados, con parada para almorzar en el Restaurante e Tapiocaria Amô."
            ),
            "duration": "Aprox. 3 horas (unos 25 km)",
            "itinerary": (
                "Punto de encuentro: Restaurante e Tapiocaria Amô\n"
                "Salida de Pipa hacia el litoral sur\n"
                "Chapadão, con parada en el mirador de la Praia do Amor\n"
                "Praia das Minas\n"
                "Acantilados y Morro Vermelho\n"
                "Piscinas naturales de Sibaúma (con marea baja)\n"
                "Cruce del río Catu\n"
                "Parada en la granja: paseo a caballo, tiro con arco, kayak y slackline\n"
                "Senderos por caminos rurales, entre Mata Atlántica y cañaverales\n"
                "Mirador de Barra de Cunhaú\n"
                "Regreso a Pipa por los acantilados\n"
                "Parada para almorzar en el Restaurante e Tapiocaria Amô"
            ),
            "included": "Cuatriciclo para hasta 2 personas\nGuía experimentado durante todo el paseo",
            "not_included": (
                "Actividades en la granja (caballo, tiro con arco, kayak y slackline)\n"
                "Almuerzo en el Restaurante e Tapiocaria Amô"
            ),
            "important_info": QUAD_RULES_ES,
            "meta_title": "Paseo en cuatriciclo en Pipa – Ruta 2",
            "meta_description": "Cuatriciclo en Pipa: acantilados, Morro Vermelho, piscinas de Sibaúma, cruce del río Catu, Mata Atlántica y mirador de Barra de Cunhaú. 3 horas.",
        },
    },
    {
        "slug": "quad-bike-tour-north-coast",
        "cadastur_guide": True,
        "tide_dependent": True,
        "category": "adventure-tours",
        "featured": False,
        "order": 6,
        "price": None,  # not informed yet -> "price on request"
        "pt": {
            "title": "Quadriciclo Litoral Norte: mirantes, Praia do Giz e dunas de Cacimbinhas",
            "summary": "Quadriciclo pelo litoral norte, com mirantes sobre a Lagoa de Guaraíras e as praias de Pipa, banho na Praia do Giz e trilha na Mata Atlântica.",
            "description": (
                "Um passeio para pilotar com calma e aproveitar a paisagem. Não é corrida nem off-road radical: "
                "você segue o guia o tempo todo e para nos pontos mais bonitos do litoral norte de Pipa.\n\n"
                "A saída é da base em Tibau do Sul, a cerca de 8 km do centro de Pipa, depois de um treinamento "
                "rápido sobre o quadriciclo. A primeira parada é o mirante da Lagoa de Guaraíras. Em seguida vem a "
                "Praia do Giz, que se alcança por uma escadaria com vista para o mar. Com a maré baixa, formam-se "
                "piscinas naturais de água clara.\n\n"
                "Por caminhos alternativos, o passeio chega ao mirante de Cacimbinhas, de onde se vê a Praia do "
                "Centro, a Baía dos Golfinhos, a Praia do Madeiro e a própria Cacimbinhas. O final é pelas dunas de "
                "Cacimbinhas e por uma trilha fechada de Mata Atlântica. Na saída das 15h, o banho dá lugar ao pôr "
                "do sol no alto das dunas."
            ),
            "duration": "Saídas às 9h, 12h e 15h",
            "itinerary": (
                "Treinamento teórico e prático na base, em Tibau do Sul\n"
                "Mirante da Lagoa de Guaraíras\n"
                "Praia do Giz: descida pela escadaria e banho (saídas das 9h e 12h)\n"
                "Mirante de Cacimbinhas, por caminhos alternativos\n"
                "Parque de dunas de Cacimbinhas\n"
                "Trilha em Mata Atlântica fechada\n"
                "Pôr do sol no alto das dunas de Cacimbinhas (saída das 15h)"
            ),
            "included": "Treinamento antes do passeio\nGuia acompanhando todo o trajeto",
            "not_included": "",
            "important_info": (
                "Saídas às 9h, 12h e 15h\n"
                "Ponto de partida: base em Tibau do Sul, a cerca de 8 km do centro de Pipa (a localização é enviada pelo WhatsApp)\n"
                "Não é corrida nem off-road: o grupo segue o guia durante todo o trajeto\n"
                "As piscinas naturais da Praia do Giz se formam com a maré baixa\n"
                "O acesso à Praia do Giz é por uma escadaria\n"
                "Na saída das 15h, a parada para banho é substituída pelo pôr do sol nas dunas"
            ),
            "meta_title": "Passeio de quadriciclo em Pipa – Litoral Norte",
            "meta_description": "Quadriciclo no litoral norte de Pipa: mirante da Lagoa de Guaraíras, Praia do Giz, mirante de Cacimbinhas, dunas e trilha na Mata Atlântica.",
        },
        "en": {
            "title": "Quad Bike Tour – North Coast: Viewpoints, Praia do Giz & Cacimbinhas Dunes",
            "summary": "Quad bike tour along the north coast, with viewpoints over Guaraíras Lagoon and Pipa's beaches, a swim at Praia do Giz and an Atlantic Forest trail.",
            "description": (
                "A tour to ride at an easy pace and enjoy the scenery. It is not a race or an extreme off-road ride: "
                "you follow the guide the whole way and stop at the most beautiful spots on Pipa's north coast.\n\n"
                "It starts from the base in Tibau do Sul, about 8 km from the centre of Pipa, after a short training "
                "session on the quad bike. The first stop is the Guaraíras Lagoon viewpoint. Next comes Praia do Giz, "
                "reached by a staircase with sea views. At low tide, natural pools with clear water form there.\n\n"
                "Along alternative tracks, the tour reaches the Cacimbinhas viewpoint, overlooking Praia do Centro, "
                "Dolphin Bay, Madeiro Beach and Cacimbinhas itself. It ends through the Cacimbinhas dunes and a dense "
                "Atlantic Forest trail. On the 3 pm departure, the swim is replaced by sunset on top of the dunes."
            ),
            "duration": "Departures at 9 am, 12 pm and 3 pm",
            "itinerary": (
                "Theory and practical training at the base in Tibau do Sul\n"
                "Guaraíras Lagoon viewpoint\n"
                "Praia do Giz: walk down the staircase and swim (9 am and 12 pm departures)\n"
                "Cacimbinhas viewpoint, along alternative tracks\n"
                "Cacimbinhas dune park\n"
                "Trail through dense Atlantic Forest\n"
                "Sunset on top of the Cacimbinhas dunes (3 pm departure)"
            ),
            "included": "Training before the tour\nGuide throughout the route",
            "not_included": "",
            "important_info": (
                "Departures at 9 am, 12 pm and 3 pm\n"
                "Starting point: base in Tibau do Sul, about 8 km from the centre of Pipa (location sent by WhatsApp)\n"
                "Not a race or off-road ride: the group follows the guide the whole way\n"
                "The natural pools at Praia do Giz form at low tide\n"
                "Praia do Giz is reached by a staircase\n"
                "On the 3 pm departure, the swim stop is replaced by sunset on the dunes"
            ),
            "meta_title": "Quad Bike Tour in Pipa, Brazil – North Coast",
            "meta_description": "Pipa quad bike tour on the north coast: Guaraíras Lagoon viewpoint, Praia do Giz, Cacimbinhas viewpoint, dunes and an Atlantic Forest trail.",
        },
        "es": {
            "title": "Cuatriciclo Litoral Norte: miradores, Praia do Giz y dunas de Cacimbinhas",
            "summary": "Cuatriciclo por el litoral norte, con miradores sobre la Laguna de Guaraíras y las playas de Pipa, baño en la Praia do Giz y sendero en la Mata Atlántica.",
            "description": (
                "Un paseo para manejar con calma y disfrutar del paisaje. No es una carrera ni un off-road extremo: "
                "sigues al guía todo el tiempo y paras en los puntos más lindos del litoral norte de Pipa.\n\n"
                "La salida es desde la base en Tibau do Sul, a unos 8 km del centro de Pipa, después de una breve "
                "capacitación sobre el cuatriciclo. La primera parada es el mirador de la Laguna de Guaraíras. Luego "
                "viene la Praia do Giz, a la que se baja por una escalera con vista al mar. Con marea baja se forman "
                "piscinas naturales de agua clara.\n\n"
                "Por caminos alternativos, el paseo llega al mirador de Cacimbinhas, desde donde se ven la Praia do "
                "Centro, la Bahía de los Delfines, la Praia do Madeiro y la propia Cacimbinhas. El final es por las "
                "dunas de Cacimbinhas y un sendero cerrado de Mata Atlántica. En la salida de las 15 h, el baño se "
                "cambia por el atardecer en lo alto de las dunas."
            ),
            "duration": "Salidas a las 9, 12 y 15 h",
            "itinerary": (
                "Capacitación teórica y práctica en la base, en Tibau do Sul\n"
                "Mirador de la Laguna de Guaraíras\n"
                "Praia do Giz: bajada por la escalera y baño (salidas de las 9 y 12 h)\n"
                "Mirador de Cacimbinhas, por caminos alternativos\n"
                "Parque de dunas de Cacimbinhas\n"
                "Sendero por Mata Atlántica cerrada\n"
                "Atardecer en lo alto de las dunas de Cacimbinhas (salida de las 15 h)"
            ),
            "included": "Capacitación antes del paseo\nGuía durante todo el recorrido",
            "not_included": "",
            "important_info": (
                "Salidas a las 9, 12 y 15 h\n"
                "Punto de partida: base en Tibau do Sul, a unos 8 km del centro de Pipa (la ubicación se envía por WhatsApp)\n"
                "No es una carrera ni off-road: el grupo sigue al guía durante todo el recorrido\n"
                "Las piscinas naturales de la Praia do Giz se forman con marea baja\n"
                "A la Praia do Giz se accede por una escalera\n"
                "En la salida de las 15 h, la parada para nadar se cambia por el atardecer en las dunas"
            ),
            "meta_title": "Paseo en cuatriciclo en Pipa – Litoral Norte",
            "meta_description": "Cuatriciclo en el litoral norte de Pipa: mirador de la Laguna de Guaraíras, Praia do Giz, mirador de Cacimbinhas, dunas y sendero en la Mata Atlántica.",
        },
    },
]

TEXT_FIELDS = ["title", "summary", "description", "duration", "itinerary", "included", "not_included",
               "important_info", "meta_title", "meta_description"]
SUFFIX = {"en": "en", "pt": "pt", "es": "es"}


class Command(BaseCommand):
    help = "Create or update TravelPipa's real experiences (boat, jeep, Guaraíras and quad bike tours)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace-media", action="store_true",
            help="Substitui as fotos e o vídeo dos passeios que têm arquivos na pasta content/ "
                 "(apaga os que estão no site para esses passeios).")
        parser.add_argument(
            "--only-new", action="store_true",
            help="Só cria os passeios que ainda não existem; não altera os que já estão no site.")

    @transaction.atomic
    def handle(self, *args, **options):
        self.replace_media = options.get("replace_media", False)
        only_new = options.get("only_new", False)
        categories = {}
        for slug, data in CATEGORIES.items():
            cat, _ = Category.objects.get_or_create(slug=slug, defaults=data)
            categories[slug] = cat

        for tour in TOURS:
            if only_new and Experience.objects.filter(slug=tour["slug"]).exists():
                continue
            values = {
                "category": categories[tour["category"]],
                "featured": tour["featured"],
                "order": tour["order"],
                "price": tour["price"],
                "currency": "BRL",
                "is_demo": False,
                "active": True,
                "tide_dependent": tour.get("tide_dependent", False),
                "cadastur_guide": tour.get("cadastur_guide", False),
            }
            for field in ("transfer_type", "max_passengers"):
                if field in tour:
                    values[field] = tour[field]
            if tour.get("price_unit"):
                values["price_unit"] = tour["price_unit"]
                values["price_is_starting"] = tour["price_is_starting"]
            for lang, suffix in SUFFIX.items():
                for field in TEXT_FIELDS:
                    values[f"{field}_{suffix}"] = tour[lang][field]
                for field in ("origin", "destination"):  # transfers only
                    if field in tour[lang]:
                        values[f"{field}_{suffix}"] = tour[lang][field]
            if tour["slug"] == price_table_wording.SLUG:
                values["transfer_rates"] = price_table_wording.RATES
                values["group_from"] = price_table_wording.GROUP_FROM
                for name, value in list(values.items()):
                    if isinstance(value, str):
                        values[name] = price_table_wording.apply(value)
            for name, value in values.items():
                limit = getattr(Experience._meta.get_field(name), "max_length", None)
                if limit and isinstance(value, str) and len(value) > limit:
                    self.stdout.write(self.style.WARNING(f"  Texto cortado em {limit} caracteres: {name}"))
                    values[name] = value[:limit]
            obj, created = Experience.objects.update_or_create(slug=tour["slug"], defaults=values)
            self.stdout.write(self.style.SUCCESS(f"{'Criada' if created else 'Atualizada'}: {obj.title_pt}"))
            if tour.get("media"):
                self.attach_media(obj, tour["media"])

        if only_new:
            return
        self.attach_site_images()
        self.stdout.write("Envie as fotos de cada passeio pelo painel (Experiências / passeios).")

    def attach_site_images(self):
        """Banner and other site images: only set when empty in the admin (or with --replace-media)."""
        site = SiteSettings.load()
        changed = False
        for field, rel_path in SITE_IMAGES.items():
            source = CONTENT_DIR / rel_path
            current = getattr(site, field)
            if not source.exists() or (current and not self.replace_media):
                continue
            if current:
                current.delete(save=False)
            with source.open("rb") as fh:
                getattr(site, field).save(source.name, File(fh), save=False)
            changed = True
            self.stdout.write(f"  Imagem do site definida: {field}")
        if changed:
            site.save()

    def attach_media(self, experience, media):
        """Add photos/video from CONTENT_DIR, only when the experience has none yet
        (never overwrites what the team uploaded in the admin panel), unless --replace-media."""
        if self.replace_media:
            for image in experience.images.all():
                image.image.delete(save=False)
                image.delete()
            if media.get("video") and experience.video:
                experience.video.delete(save=False)
                experience.video_poster.delete(save=False)
                experience.save(update_fields=["video", "video_poster"])
        if media.get("photos"):
            existing = {Path(img.image.name).stem: img for img in experience.images.all()}
            had_cover = any(img.is_cover for img in existing.values())
            added = 0
            for order, (rel_path, alt_pt, alt_en, alt_es, *rest) in enumerate(media["photos"]):
                album = rest[0] if rest else ExperienceImage.Album.MAIN
                source = CONTENT_DIR / rel_path
                if not source.exists():
                    self.stdout.write(self.style.WARNING(f"  Foto não encontrada: {rel_path}"))
                    continue
                # Already on the site? (Django may add a suffix like _aB3dE9f to repeated names)
                match = next((img for stem, img in existing.items()
                              if stem == source.stem or stem.startswith(source.stem + "_")), None)
                if match:
                    if match.order != order or match.album != album:
                        match.order, match.album = order, album
                        match.save()
                    continue
                image = ExperienceImage(experience=experience, order=order, album=album,
                                        is_cover=(order == 0 and not had_cover and not album),
                                        alt_pt=alt_pt, alt_en=alt_en, alt_es=alt_es)
                with source.open("rb") as fh:
                    image.image.save(source.name, File(fh), save=False)
                image.save()
                added += 1
            if added:
                self.stdout.write(f"  {added} foto(s) adicionada(s)")

        if media.get("video") and not experience.video:
            source = CONTENT_DIR / media["video"]
            if source.exists():
                with source.open("rb") as fh:
                    experience.video.save(source.name, File(fh), save=False)
                poster = CONTENT_DIR / media.get("video_poster", "")
                if media.get("video_poster") and poster.exists():
                    with poster.open("rb") as fh:
                        experience.video_poster.save(poster.name, File(fh), save=False)
                experience.save(update_fields=["video", "video_poster"])
                self.stdout.write("  Vídeo adicionado")
