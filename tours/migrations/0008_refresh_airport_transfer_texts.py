"""
Brings the airport transfer texts on the live site up to date (price per car,
negotiated round-trip discount, 10% deposit) — but only fields that still hold
exactly the text loaded by the previous version. Anything edited in the panel
is left untouched.
"""
from django.db import migrations

# slug -> field -> [text loaded by the previous version, new text]
UPDATES = {'natal-airport-pipa-transfer': {'description_en': ['Start and end your trip without worries: a car with '
                                                    'driver takes you from Natal International Airport to '
                                                    'your accommodation in Pipa, or back again.\n'
                                                    '\n'
                                                    'Our fleet includes 7-seat cars, ideal for families and '
                                                    'groups with more luggage. We also handle large groups: '
                                                    'tell us how many people are travelling and we suggest '
                                                    'the best option.\n'
                                                    '\n'
                                                    'Send us your flight number, arrival time, number of '
                                                    'passengers and pieces of luggage. With these details we '
                                                    'send you a quote and confirm everything before you '
                                                    'travel.',
                                                    'Start and end your trip without worries: a car with '
                                                    'driver takes you from Natal International Airport to '
                                                    'your accommodation in Pipa, or back again.\n'
                                                    '\n'
                                                    'The price is per car, for up to 3 people. For families '
                                                    'and larger groups we have 7-seat cars and options for '
                                                    'large groups: tell us how many people are travelling '
                                                    'and we suggest the best option.\n'
                                                    '\n'
                                                    'We negotiate a discount for round trips. Include your '
                                                    'flight number and arrival time when you book; we then '
                                                    'contact you with the pickup details and the 10% deposit '
                                                    'that secures your booking.'],
                                 'description_es': ['Empieza y termina tu viaje sin preocupaciones: un coche '
                                                    'con conductor te lleva desde el Aeropuerto '
                                                    'Internacional de Natal hasta tu alojamiento en Pipa, o '
                                                    'hace el camino de vuelta.\n'
                                                    '\n'
                                                    'La flota incluye coches de 7 plazas, ideales para '
                                                    'familias y grupos con más equipaje. También atendemos '
                                                    'grupos grandes: cuéntanos cuántas personas viajan y te '
                                                    'indicamos la mejor opción.\n'
                                                    '\n'
                                                    'Envíanos tu número de vuelo, la hora de llegada, la '
                                                    'cantidad de pasajeros y de maletas. Con estos datos te '
                                                    'enviamos el presupuesto y confirmamos todo antes del '
                                                    'viaje.',
                                                    'Empieza y termina tu viaje sin preocupaciones: un coche '
                                                    'con conductor te lleva desde el Aeropuerto '
                                                    'Internacional de Natal hasta tu alojamiento en Pipa, o '
                                                    'hace el camino de vuelta.\n'
                                                    '\n'
                                                    'El precio es por coche, para hasta 3 personas. Para '
                                                    'familias y grupos más grandes tenemos coches de 7 '
                                                    'plazas y opciones para grupos grandes: cuéntanos '
                                                    'cuántas personas viajan y te indicamos la mejor '
                                                    'opción.\n'
                                                    '\n'
                                                    'Negociamos un descuento si cierras ida y vuelta. Indica '
                                                    'tu número de vuelo y la hora de llegada al reservar; '
                                                    'después te contactamos con los detalles de la recogida '
                                                    'y la seña del 10% que garantiza tu reserva.'],
                                 'description_pt': ['Comece e termine a viagem sem preocupação: um carro com '
                                                    'motorista leva você do Aeroporto Internacional de Natal '
                                                    'até a sua hospedagem em Pipa, ou faz o caminho de '
                                                    'volta.\n'
                                                    '\n'
                                                    'A frota inclui carros de 7 lugares, ideais para '
                                                    'famílias e grupos com mais bagagem. Também atendemos '
                                                    'grupos grandes: conte quantas pessoas viajam e '
                                                    'indicamos a melhor opção.\n'
                                                    '\n'
                                                    'Envie o número do voo, o horário de chegada, a '
                                                    'quantidade de passageiros e de malas. Com essas '
                                                    'informações, mandamos o orçamento e confirmamos todos '
                                                    'os detalhes antes da viagem.',
                                                    'Comece e termine a viagem sem preocupação: um carro com '
                                                    'motorista leva você do Aeroporto Internacional de Natal '
                                                    'até a sua hospedagem em Pipa, ou faz o caminho de '
                                                    'volta.\n'
                                                    '\n'
                                                    'O valor é por carro, para até 3 pessoas. Para famílias '
                                                    'e grupos maiores, temos carros de 7 lugares e opções '
                                                    'para grupos grandes: informe quantas pessoas viajam e '
                                                    'indicamos a melhor opção.\n'
                                                    '\n'
                                                    'Negociamos desconto fechando ida e volta. Reserve '
                                                    'informando o número do voo e o horário de chegada; '
                                                    'depois entramos em contato com os detalhes do embarque '
                                                    'e o sinal de 10% que garante a sua reserva.'],
                                 'important_info_en': ['Vehicles registered for tourist transport with '
                                                       'DER/RN (Rio Grande do Norte transport authority)\n'
                                                       '7-seat cars available for families and groups\n'
                                                       'Large groups: tell us how many people and we '
                                                       'organise the best option\n'
                                                       'Include your flight number and arrival time in the '
                                                       'request\n'
                                                       'Tell us how many passengers and bags so we can '
                                                       'suggest the right car\n'
                                                       'We also do the return trip, from Pipa to the airport',
                                                       'Price per car, for up to 3 people\n'
                                                       '7-seat cars and large groups: price on request\n'
                                                       'We negotiate a discount for round trips\n'
                                                       'Vehicles registered for tourist transport with '
                                                       'DER/RN (Rio Grande do Norte transport authority)\n'
                                                       'Include your flight number and arrival time when you '
                                                       'book\n'
                                                       'Tell us how many bags you have so we can suggest the '
                                                       'right car'],
                                 'important_info_es': ['Vehículos registrados para transporte turístico en '
                                                       'el DER/RN (órgano de transporte de Rio Grande do '
                                                       'Norte)\n'
                                                       'Coches de 7 plazas disponibles para familias y '
                                                       'grupos\n'
                                                       'Grupos grandes: indícanos el número de personas y '
                                                       'organizamos la mejor opción\n'
                                                       'Indica tu número de vuelo y la hora de llegada en la '
                                                       'solicitud\n'
                                                       'Indícanos cuántos pasajeros y maletas viajan para '
                                                       'sugerir el coche adecuado\n'
                                                       'También hacemos el trayecto de vuelta, de Pipa al '
                                                       'aeropuerto',
                                                       'Precio por coche, para hasta 3 personas\n'
                                                       'Coches de 7 plazas y grupos grandes: precio a '
                                                       'consultar\n'
                                                       'Negociamos un descuento si cierras ida y vuelta\n'
                                                       'Vehículos registrados para transporte turístico en '
                                                       'el DER/RN (órgano de transporte de Rio Grande do '
                                                       'Norte)\n'
                                                       'Indica tu número de vuelo y la hora de llegada al '
                                                       'reservar\n'
                                                       'Indícanos cuántas maletas llevas para sugerir el '
                                                       'coche adecuado'],
                                 'important_info_pt': ['Veículos cadastrados para transporte turístico no '
                                                       'DER/RN\n'
                                                       'Carros de 7 lugares disponíveis para famílias e '
                                                       'grupos\n'
                                                       'Grupos grandes: informe o número de pessoas e '
                                                       'organizamos a melhor opção\n'
                                                       'Informe o número do voo e o horário de chegada na '
                                                       'solicitação\n'
                                                       'Informe a quantidade de passageiros e de malas para '
                                                       'indicarmos o carro certo\n'
                                                       'Também fazemos o trajeto de volta, de Pipa para o '
                                                       'aeroporto',
                                                       'Valor por carro, para até 3 pessoas\n'
                                                       'Carros de 7 lugares e grupos grandes: valor sob '
                                                       'consulta\n'
                                                       'Negociamos desconto fechando ida e volta\n'
                                                       'Veículos cadastrados para transporte turístico no '
                                                       'DER/RN\n'
                                                       'Informe o número do voo e o horário de chegada na '
                                                       'reserva\n'
                                                       'Informe a quantidade de malas para indicarmos o '
                                                       'carro certo'],
                                 'meta_description_en': ['Natal airport transfer to Pipa with driver: 7-seat '
                                                         'cars and options for large groups. Send your '
                                                         'flight details and get a quote from TravelPipa.',
                                                         'Natal airport transfer to Pipa with driver from R$ '
                                                         '240 per car (up to 3 people). 7-seat cars for '
                                                         'groups and a negotiable round-trip discount.'],
                                 'meta_description_es': ['Traslado del aeropuerto de Natal a Pipa con '
                                                         'conductor: coches de 7 plazas y opciones para '
                                                         'grupos grandes. Envía tu vuelo y recibe el '
                                                         'presupuesto.',
                                                         'Traslado del aeropuerto de Natal a Pipa con '
                                                         'conductor desde R$ 240 por coche (hasta 3 '
                                                         'personas). Coches de 7 plazas para grupos y '
                                                         'descuento negociable en ida y vuelta.'],
                                 'meta_description_pt': ['Transfer com motorista entre o Aeroporto de Natal '
                                                         'e Pipa, com carros de 7 lugares e opções para '
                                                         'grupos grandes. Envie seu voo e receba o '
                                                         'orçamento.',
                                                         'Transfer com motorista entre o Aeroporto de Natal '
                                                         'e Pipa a partir de R$ 240 por carro (até 3 '
                                                         'pessoas). Carros de 7 lugares e desconto negociado '
                                                         'na ida e volta.'],
                                 'summary_en': ['Car with driver between Natal Airport and Pipa, with 7-seat '
                                                'options and solutions for large groups.',
                                                'Car with driver between Natal Airport and Pipa. Price per '
                                                'car for up to 3 people.'],
                                 'summary_es': ['Coche con conductor entre el Aeropuerto de Natal y Pipa, '
                                                'con opciones de 7 plazas y atención para grupos grandes.',
                                                'Coche con conductor entre el Aeropuerto de Natal y Pipa. '
                                                'Precio por coche, hasta 3 personas.'],
                                 'summary_pt': ['Carro com motorista entre o Aeroporto de Natal e Pipa, com '
                                                'opções de 7 lugares e atendimento para grupos grandes.',
                                                'Carro com motorista entre o Aeroporto de Natal e Pipa. '
                                                'Valor por carro, para até 3 pessoas.']}}


def forwards(apps, schema_editor):
    Experience = apps.get_model("tours", "Experience")
    for slug, fields in UPDATES.items():
        exp = Experience.objects.filter(slug=slug).first()
        if not exp:
            continue
        changed = []
        for name, (old, new) in fields.items():
            if (getattr(exp, name) or "").strip() == old.strip():
                limit = Experience._meta.get_field(name).max_length
                setattr(exp, name, new[:limit] if limit else new)
                changed.append(name)
        if changed:
            exp.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("tours", "0007_round_trip_wording")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
