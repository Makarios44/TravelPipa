"""
Creates demonstration content so the website can be previewed and tested.

Everything created here is clearly marked as demo (``is_demo=True`` and a
"Demo" badge on the site). No prices, reviews or commercial conditions are
invented. Run again safely: existing items are left untouched.

    python manage.py seed_demo
    python manage.py seed_demo --remove     # delete demo experiences and their images
"""
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from core.demo_images import scene_bytes
from core.models import SiteSettings
from tours.models import Category, Experience, ExperienceImage

CATEGORIES = [
    # slug, icon, is_transfer, (en, pt, es)
    ("boat-experiences", "water", False, ("Boat Experiences", "Passeios de barco", "Paseos en barco")),
    ("adventure-tours", "compass", False, ("Adventure Tours", "Aventura", "Aventura")),
    ("nature-beaches", "tree", False, ("Nature & Beaches", "Natureza e praias", "Naturaleza y playas")),
    ("local-experiences", "people", False, ("Local Experiences", "Experiências locais", "Experiencias locales")),
    ("transfers", "car-front", True, ("Transfers", "Transfers", "Traslados")),
]

DEMO_EXPERIENCES = [
    {
        "slug": "dolphin-bay-boat-tour",
        "category": "boat-experiences",
        "variant": "boat",
        "featured": True,
        "order": 1,
        "title": ("Boat Tour to Dolphin Bay", "Passeio de barco à Baía dos Golfinhos", "Paseo en barco a la Bahía de los Delfines"),
        "summary": (
            "Sail along the cliffs of Pipa towards Dolphin Bay, with a stop for swimming when the sea allows.",
            "Navegue junto às falésias de Pipa até a Baía dos Golfinhos, com parada para banho quando o mar permitir.",
            "Navega junto a los acantilados de Pipa hacia la Bahía de los Delfines, con parada para nadar si el mar lo permite.",
        ),
        "description": (
            "Example description. This boat trip follows the coastline of Pipa, passing the coloured cliffs and the beaches between the village and Dolphin Bay.\n\nDolphins are often seen in the bay, but sightings depend on nature and cannot be guaranteed. Replace this text with the real description provided by the operator.",
            "Descrição de exemplo. O passeio de barco segue o litoral de Pipa, passando pelas falésias coloridas e pelas praias entre a vila e a Baía dos Golfinhos.\n\nOs golfinhos costumam aparecer na baía, mas o avistamento depende da natureza e não pode ser garantido. Substitua este texto pela descrição real fornecida pelo operador.",
            "Descripción de ejemplo. El paseo en barco sigue la costa de Pipa, pasando por los acantilados de colores y las playas entre el pueblo y la Bahía de los Delfines.\n\nEs habitual ver delfines en la bahía, pero el avistamiento depende de la naturaleza y no se puede garantizar. Sustituye este texto por la descripción real del operador.",
        ),
        "duration": ("Example: approx. 2 hours", "Exemplo: aprox. 2 horas", "Ejemplo: aprox. 2 horas"),
        "itinerary": (
            "Meeting point in Pipa (to be confirmed)\nBoat ride along the cliffs\nDolphin Bay\nStop for swimming (sea conditions permitting)\nReturn to the starting point",
            "Ponto de encontro em Pipa (a confirmar)\nNavegação junto às falésias\nBaía dos Golfinhos\nParada para banho (conforme as condições do mar)\nRetorno ao ponto de partida",
            "Punto de encuentro en Pipa (a confirmar)\nNavegación junto a los acantilados\nBahía de los Delfines\nParada para nadar (según las condiciones del mar)\nRegreso al punto de partida",
        ),
        "included": ("Example item: boat ride\nExample item: life jackets", "Item de exemplo: passeio de barco\nItem de exemplo: coletes salva-vidas", "Ítem de ejemplo: paseo en barco\nÍtem de ejemplo: chalecos salvavidas"),
        "not_included": ("Example item: food and drinks", "Item de exemplo: alimentação e bebidas", "Ítem de ejemplo: comida y bebidas"),
        "important": (
            "Departure times depend on the tide and sea conditions\nBring sunscreen, a hat and water",
            "Os horários dependem da maré e das condições do mar\nLeve protetor solar, chapéu e água",
            "Los horarios dependen de la marea y del estado del mar\nLleva protector solar, gorra y agua",
        ),
    },
    {
        "slug": "southern-coast-buggy-tour",
        "category": "adventure-tours",
        "variant": "buggy",
        "featured": True,
        "order": 2,
        "title": ("Buggy Tour along the Southern Coast", "Passeio de buggy pelo litoral sul", "Paseo en buggy por el litoral sur"),
        "summary": (
            "Dunes, lagoons and beaches of the southern coast of Rio Grande do Norte by buggy.",
            "Dunas, lagoas e praias do litoral sul do Rio Grande do Norte de buggy.",
            "Dunas, lagunas y playas del litoral sur de Rio Grande do Norte en buggy.",
        ),
        "description": (
            "Example description. A buggy tour is one of the classic ways to explore the region around Pipa, combining beaches, dunes and viewpoints.\n\nThe exact route depends on the operator and the tide. Replace this text with the real route and details.",
            "Descrição de exemplo. O passeio de buggy é uma das formas clássicas de conhecer a região de Pipa, combinando praias, dunas e mirantes.\n\nO roteiro exato depende do operador e da maré. Substitua este texto pelo roteiro e detalhes reais.",
            "Descripción de ejemplo. El paseo en buggy es una de las formas clásicas de conocer la región de Pipa, combinando playas, dunas y miradores.\n\nLa ruta exacta depende del operador y de la marea. Sustituye este texto por la ruta y los detalles reales.",
        ),
        "duration": ("Example: half day", "Exemplo: meio período", "Ejemplo: medio día"),
        "itinerary": (
            "Pickup in Pipa (to be confirmed)\nBeaches and viewpoints of the southern coast\nDunes and lagoon stop\nReturn to Pipa",
            "Saída de Pipa (a confirmar)\nPraias e mirantes do litoral sul\nParada em dunas e lagoa\nRetorno a Pipa",
            "Salida desde Pipa (a confirmar)\nPlayas y miradores del litoral sur\nParada en dunas y laguna\nRegreso a Pipa",
        ),
        "included": ("Example item: buggy with driver", "Item de exemplo: buggy com motorista", "Ítem de ejemplo: buggy con conductor"),
        "not_included": ("Example item: entrance fees, if any\nExample item: meals", "Item de exemplo: taxas de entrada, se houver\nItem de exemplo: refeições", "Ítem de ejemplo: tasas de entrada, si las hay\nÍtem de ejemplo: comidas"),
        "important": ("Route may change according to the tide", "O roteiro pode mudar conforme a maré", "La ruta puede cambiar según la marea"),
    },
    {
        "slug": "atlantic-forest-trail-natural-pools",
        "category": "nature-beaches",
        "variant": "nature",
        "featured": True,
        "order": 3,
        "title": ("Atlantic Forest Trail & Natural Pools", "Trilha na Mata Atlântica e piscinas naturais", "Sendero en la Mata Atlántica y piscinas naturales"),
        "summary": (
            "A guided walk through coastal forest and cliff viewpoints, timed with low tide for the natural pools.",
            "Caminhada guiada pela mata costeira e mirantes das falésias, combinada com a maré baixa para as piscinas naturais.",
            "Caminata guiada por el bosque costero y miradores, coordinada con la marea baja para las piscinas naturales.",
        ),
        "description": (
            "Example description. Pipa is surrounded by protected Atlantic Forest and cliffs with views over the sea. At low tide, natural pools form between the rocks on some beaches.\n\nReplace this text with the real description, difficulty level and meeting point.",
            "Descrição de exemplo. Pipa é cercada por Mata Atlântica preservada e falésias com vista para o mar. Na maré baixa, formam-se piscinas naturais entre as pedras em algumas praias.\n\nSubstitua este texto pela descrição real, nível de dificuldade e ponto de encontro.",
            "Descripción de ejemplo. Pipa está rodeada de Mata Atlántica protegida y acantilados con vistas al mar. Con la marea baja se forman piscinas naturales entre las rocas en algunas playas.\n\nSustituye este texto por la descripción real, el nivel de dificultad y el punto de encuentro.",
        ),
        "duration": ("Example: approx. 3 hours", "Exemplo: aprox. 3 horas", "Ejemplo: aprox. 3 horas"),
        "itinerary": (
            "Forest trail\nCliff viewpoints\nBeach with natural pools at low tide",
            "Trilha na mata\nMirantes nas falésias\nPraia com piscinas naturais na maré baixa",
            "Sendero en el bosque\nMiradores en los acantilados\nPlaya con piscinas naturales en marea baja",
        ),
        "included": ("Example item: local guide", "Item de exemplo: guia local", "Ítem de ejemplo: guía local"),
        "not_included": ("Example item: transport to the meeting point", "Item de exemplo: transporte até o ponto de encontro", "Ítem de ejemplo: transporte al punto de encuentro"),
        "important": ("Wear comfortable shoes\nSchedule depends on the tide table", "Use calçado confortável\nHorário depende da tábua de marés", "Usa calzado cómodo\nEl horario depende de la tabla de mareas"),
    },
    {
        "slug": "natal-airport-to-pipa-transfer",
        "category": "transfers",
        "variant": "car",
        "featured": True,
        "order": 1,
        "origin": ("Natal International Airport (NAT)", "Aeroporto Internacional de Natal (NAT)", "Aeropuerto Internacional de Natal (NAT)"),
        "destination": ("Praia da Pipa", "Praia da Pipa", "Praia da Pipa"),
        "transfer_type": "private",
        "max_passengers": 4,
        "title": ("Private Transfer: Natal Airport → Pipa", "Transfer privativo: Aeroporto de Natal → Pipa", "Traslado privado: Aeropuerto de Natal → Pipa"),
        "summary": (
            "Private car from Natal International Airport to your accommodation in Pipa.",
            "Carro privativo do Aeroporto Internacional de Natal até sua hospedagem em Pipa.",
            "Coche privado desde el Aeropuerto Internacional de Natal hasta tu alojamiento en Pipa.",
        ),
        "description": (
            "Example description. Send your flight number and arrival time, and we organise a private car from Natal International Airport to your accommodation in Pipa.\n\nReplace this text with the real conditions: vehicle type, luggage allowance and waiting time.",
            "Descrição de exemplo. Envie o número do voo e o horário de chegada, e organizamos um carro privativo do Aeroporto Internacional de Natal até sua hospedagem em Pipa.\n\nSubstitua este texto pelas condições reais: tipo de veículo, bagagem e tempo de espera.",
            "Descripción de ejemplo. Envía tu número de vuelo y hora de llegada, y organizamos un coche privado desde el Aeropuerto Internacional de Natal hasta tu alojamiento en Pipa.\n\nSustituye este texto por las condiciones reales: tipo de vehículo, equipaje y tiempo de espera.",
        ),
        "duration": ("Example: approx. 1h15 drive", "Exemplo: aprox. 1h15 de viagem", "Ejemplo: aprox. 1h15 de viaje"),
        "itinerary": ("", "", ""),
        "included": ("Example item: private car with driver", "Item de exemplo: carro privativo com motorista", "Ítem de ejemplo: coche privado con conductor"),
        "not_included": ("", "", ""),
        "important": (
            "Include your flight number in the request",
            "Informe o número do voo na solicitação",
            "Indica tu número de vuelo en la solicitud",
        ),
    },
]


class Command(BaseCommand):
    help = "Create clearly marked demo categories and experiences (no fake prices or reviews)."

    def add_arguments(self, parser):
        parser.add_argument("--remove", action="store_true", help="Delete demo experiences instead.")
        parser.add_argument("--with-demo-contact", action="store_true",
                            help="Fill a placeholder (non-working) WhatsApp number to preview buttons. "
                                 "Never use in production.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["remove"]:
            count, _ = Experience.objects.filter(is_demo=True).delete()
            self.stdout.write(self.style.SUCCESS(f"Removed {count} demo objects."))
            return

        site = SiteSettings.load()
        if options["with_demo_contact"] and not site.whatsapp:
            site.whatsapp = "+55 00 00000-0000"
            site.save()
            self.stdout.write(self.style.WARNING("Placeholder WhatsApp set. Replace it in the admin panel."))

        categories = {}
        for order, (slug, icon, is_transfer, names) in enumerate(CATEGORIES, start=1):
            cat, created = Category.objects.get_or_create(
                slug=slug,
                defaults={"name_en": names[0], "name_pt": names[1], "name_es": names[2], "icon": icon,
                          "is_transfer": is_transfer, "order": order},
            )
            categories[slug] = cat
            self.stdout.write(("Created" if created else "Exists ") + f" category: {cat.name_en}")

        for seed, data in enumerate(DEMO_EXPERIENCES, start=1):
            if Experience.objects.filter(slug=data["slug"]).exists():
                self.stdout.write(f"Exists  experience: {data['slug']}")
                continue
            fields = {
                "category": categories[data["category"]],
                "slug": data["slug"],
                "featured": data["featured"],
                "order": data["order"],
                "is_demo": True,
                "active": True,
                "price": None,  # never invent prices
                "transfer_type": data.get("transfer_type", ""),
                "max_passengers": data.get("max_passengers"),
            }
            mapping = {"title": "title", "summary": "summary", "description": "description", "duration": "duration",
                       "itinerary": "itinerary", "included": "included", "not_included": "not_included",
                       "important": "important_info", "origin": "origin", "destination": "destination"}
            for key, field in mapping.items():
                if key not in data:
                    continue
                for suffix, value in zip(("en", "pt", "es"), data[key]):
                    fields[f"{field}_{suffix}"] = value
            exp = Experience.objects.create(**fields)
            for n in range(3 if data["variant"] != "car" else 2):
                variant = data["variant"] if n == 0 else ("beach", "sunset", data["variant"])[n % 3]
                content = ContentFile(scene_bytes(width=1600, height=1100, variant=variant, seed=seed * 10 + n,
                                                  label="DEMO IMAGE - replace with a real photo"))
                img = ExperienceImage(experience=exp, is_cover=(n == 0), order=n,
                                      alt_en=f"Demo image — {data['title'][0]}",
                                      alt_pt=f"Imagem de demonstração — {data['title'][1]}",
                                      alt_es=f"Imagen de demostración — {data['title'][2]}")
                img.image.save(f"demo-{data['slug']}-{n + 1}.jpg", content, save=False)
                img.save()
            self.stdout.write(self.style.SUCCESS(f"Created experience: {exp.title_en}"))

        self.stdout.write(self.style.SUCCESS(
            "Demo content ready. Items are marked as demo on the site; edit or remove them in the admin panel."))
