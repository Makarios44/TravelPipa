"""
Frequently asked questions: the worries customers (and the AI assistants they use)
raise before booking. One source for the page and its FAQPage schema.
"""
from django.utils.translation import gettext_lazy as _

FAQ_GROUPS = [
    (_("Trust and safety"), [
        (_("Is TravelPipa a real local agency?"),
         _("Yes. We are a small agency based in Praia da Pipa, Rio Grande do Norte. A real person from our team "
           "answers you by WhatsApp or e-mail, in English, Portuguese or Spanish, before you book and during "
           "your trip. You can read what other travellers say on our reviews page.")),
        (_("Who will drive me, and is the car registered?"),
         _("We work with a network of accredited partner drivers registered with DER/RN, the transport "
           "authority of Rio Grande do Norte, for tourist transport. Up to 12 hours before your trip we send "
           "you the driver's name, the car's model and plate, and a photo of the driver and of the car, so you "
           "know exactly who is picking you up.")),
        (_("Are the tour guides licensed?"),
         _("Yes. Our guides are registered in Cadastur, the official register of Brazil's Ministry of "
           "Tourism.")),
        (_("Can I talk to the driver before the trip?"),
         _("Yes. When we send you the driver's details we can also share the driver's WhatsApp, and our team "
           "stays available to help you during the whole trip.")),
    ]),
    (_("Booking and payment"), [
        (_("Do I have to pay to book?"),
         _("No. Booking on the website is free and takes a few minutes. Your date is secured with a 10% "
           "deposit, and the rest is paid on the day of the trip.")),
        (_("How do I pay the deposit, and is it safe?"),
         _("The 10% deposit is paid by Pix or card on a secure Mercado Pago page, through the link we send you. "
           "Your card details are entered only on Mercado Pago: we never see them and we never ask for them by "
           "WhatsApp or e-mail. When the payment goes through, your booking is marked as paid automatically.")),
        (_("How do I pay the rest?"),
         _("The remaining 90% is paid on the day, directly to the driver or guide, by Pix or in cash.")),
        (_("How do I know my booking is confirmed?"),
         _("You get a booking code as soon as you book. Our team then contacts you by WhatsApp or e-mail to "
           "confirm the details, and for transfers you receive the driver and car details up to 12 hours "
           "before the trip.")),
    ]),
    (_("Cancellations and changes"), [
        (_("What if I need to cancel?"),
         _("If you cancel at least 48 hours before the trip, we refund your deposit in full. Cancellations made "
           "less than 48 hours before are not refunded, because by then the driver or guide is already booked "
           "for you. If you just need another date, talk to us: we do our best to move your booking.")),
        (_("What if it rains heavily?"),
         _("In Pipa the sea is calm all year, so trips only change in case of heavy rain. If heavy rain makes us "
           "cancel or reschedule, you choose another date or receive your deposit back in full.")),
    ]),
    (_("Airport transfers"), [
        (_("What if my flight is delayed?"),
         _("We follow your flight, and the driver adjusts the pick-up time to your real arrival. A delayed "
           "flight costs you nothing extra.")),
        (_("Where do I meet the driver at Natal airport?"),
         _("Together with the driver's details we agree the meeting point at arrivals with you, so you know "
           "where to go as soon as you land.")),
        (_("We are 6 or more people. What do you recommend?"),
         _("For 6 people we usually recommend two cars, which costs less than renting a van. From 7 people, "
           "send us your group size and we prepare a quote.")),
    ]),
]


def faq_items():
    return [item for _group, items in FAQ_GROUPS for item in items]


def faq_schema():
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": str(q), "acceptedAnswer": {"@type": "Answer", "text": str(a)}}
            for q, a in faq_items()
        ],
    }
