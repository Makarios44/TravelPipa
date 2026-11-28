"""Transfer price table: 240 one way / 230 per leg round trip, 4 and 5 people, 2 cars for 6, group from 7."""
import datetime
import json
from decimal import Decimal
from importlib import import_module

from django.apps import apps as django_apps
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone, translation

from bookings.models import BookingRequest
from core.tests import BaseTestCase
from tours.models import Category, Experience
from tours.transfer_pricing import parse_rates, quote, summary_pt

AIRPORT_RATES = "3: 240 / 230\n4: 280 / 270\n5: 300 / 290"


class ParseRatesTests(TestCase):
    def test_reads_the_panel_format(self):
        rates = parse_rates("3: 240 / 230\n\n 4 : 280/270\n5: 300")
        self.assertEqual([(r.max_people, r.one_way, r.round_leg) for r in rates],
                         [(3, Decimal("240.00"), Decimal("230.00")), (4, Decimal("280.00"), Decimal("270.00")),
                          (5, Decimal("300.00"), Decimal("300.00"))])

    def test_rejects_bad_lines(self):
        for text in ("3 - 240", "3: 240 / 250", "3: 240\n3: 250", "3: 240\n4: 200", "0: 100"):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                parse_rates(text)


class QuoteTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name_en="Transfers", slug="transfers", is_transfer=True)
        self.t = Experience.objects.create(category=cat, title_en="Airport", origin_en="NAT", destination_en="Pipa",
                                           price=Decimal("240"), transfer_rates=AIRPORT_RATES, group_from=7)

    def check(self, people, round_trip, kind, cars, per_leg, total, savings="0"):
        q = quote(self.t, people, round_trip)
        self.assertEqual((q.kind, q.cars, q.per_leg, q.total, q.savings),
                         (kind, cars, Decimal(per_leg), Decimal(total), Decimal(savings)))

    def test_the_agreed_table(self):
        self.check(1, False, "car", [1], "240", "240")
        self.check(3, False, "car", [3], "240", "240")
        self.check(3, True, "car", [3], "230", "460", "20")
        self.check(4, False, "car", [4], "280", "280")
        self.check(4, True, "car", [4], "270", "540", "20")
        self.check(5, False, "car", [5], "300", "300")
        self.check(5, True, "car", [5], "290", "580", "20")

    def test_six_people_get_two_cars_of_three(self):
        self.check(6, False, "two_cars", [3, 3], "480", "480")
        self.check(6, True, "two_cars", [3, 3], "460", "920", "40")

    def test_seven_or_more_is_a_group(self):
        for people in (7, 12):
            self.assertTrue(quote(self.t, people, True).is_group)

    def test_no_table_means_no_quote(self):
        Experience.objects.filter(pk=self.t.pk).update(transfer_rates="")
        fresh = Experience.objects.get(pk=self.t.pk)
        self.assertIsNone(quote(fresh, 2, False))
        self.assertEqual(fresh.price_rows, [])

    def test_public_rows_and_team_summary(self):
        rows = self.t.price_rows
        self.assertEqual([(r["from"], r["to"], r["cars"], r["one_way"], r["round_leg"]) for r in rows],
                         [(1, 3, 1, Decimal("240.00"), Decimal("230.00")), (4, 4, 1, Decimal("280.00"), Decimal("270.00")),
                          (5, 5, 1, Decimal("300.00"), Decimal("290.00")), (6, 6, 2, Decimal("480.00"), Decimal("460.00"))])
        self.assertEqual(summary_pt(quote(self.t, 6, True)),
                         "2 carros (3 + 3 pessoas) · ida e volta · R$ 460 por trecho · total R$ 920")
        self.assertEqual(summary_pt(quote(self.t, 2, False)), "1 carro · só ida · R$ 240")
        self.assertEqual(summary_pt(quote(self.t, 9, False)), "Grupo de 9 pessoas — enviar orçamento")

    def test_model_validation(self):
        self.t.transfer_rates = "3: 240 / 300"
        with self.assertRaises(ValidationError) as ctx:
            self.t.full_clean()
        self.assertIn("transfer_rates", ctx.exception.message_dict)
        self.t.transfer_rates = AIRPORT_RATES
        self.t.group_from = 2
        with self.assertRaises(ValidationError) as ctx:
            self.t.full_clean()
        self.assertIn("group_from", ctx.exception.message_dict)


class BookingWithPriceTableTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.transfer.transfer_rates = AIRPORT_RATES
        self.transfer.group_from = 7
        self.transfer.price = Decimal("240")
        self.transfer.save()

    def day(self, n):
        return (timezone.localdate() + datetime.timedelta(days=n)).isoformat()

    def test_form_carries_the_prices_for_the_page(self):
        translation.activate("pt-br")
        page = self.client.get(reverse("bookings:request"))
        option = next(o for o in page.context["form"]["experience"] if str(o.data["value"]) == str(self.transfer.pk))
        quotes = json.loads(option.data["attrs"]["data-quotes"])
        self.assertEqual(quotes["group"], 7)
        self.assertEqual(quotes["rows"]["3"], {"cars": [3], "ow": "R$ 240", "leg": "R$ 230",
                                               "rt": "R$ 460", "save": "R$ 20"})
        self.assertEqual(quotes["rows"]["6"]["cars"], [3, 3])
        self.assertNotIn("7", quotes["rows"])
        self.assertContains(page, "data-quote-box")

    def test_round_trip_booking_saves_the_discounted_total(self):
        data = self.booking_payload(experience=self.transfer.pk, trip_type="round_trip", return_date=self.day(15),
                                    people=4)
        self.assertRedirects(self.client.post(reverse("bookings:request"), data), reverse("bookings:thanks"))
        booking = BookingRequest.objects.get()
        self.assertEqual(booking.quoted_total, Decimal("540.00"))
        self.assertEqual(booking.quote_summary, "1 carro · ida e volta · R$ 270 por trecho · total R$ 540")
        thanks = self.client.get(reverse("bookings:thanks"))
        self.assertContains(thanks, "Round trip, with discount: total R$ 540")
        self.assertNotContains(thanks, "we negotiate your discount")

    def test_one_way_and_group(self):
        url = reverse("bookings:request")
        self.client.post(url, self.booking_payload(experience=self.transfer.pk, people=2))
        self.client.post(url, self.booking_payload(experience=self.transfer.pk, people=9, email="b@example.com"))
        one, group = BookingRequest.objects.order_by("created_at")
        self.assertEqual((one.quoted_total, one.quote_summary), (Decimal("240.00"), "1 carro · só ida · R$ 240"))
        self.assertIsNone(group.quoted_total)
        self.assertEqual(group.quote_summary, "Grupo de 9 pessoas — enviar orçamento")

    def test_transfer_page_shows_the_table(self):
        translation.activate("pt-br")
        page = self.client.get(self.transfer.get_absolute_url())
        self.assertContains(page, 'class="price-table"')
        for text in ("Até 3", "R$ 240", "R$ 230", "R$ 280", "R$ 300", "6 · 2 carros", "7 ou mais",
                     "2 carros saem mais barato que alugar uma van."):
            self.assertContains(page, text)
        listing = self.client.get(reverse("tours:transfers"))
        self.assertContains(listing, "Ida e volta: cada trecho sai mais barato")


class AirportMigrationTests(TestCase):
    def test_fills_the_table_and_only_rewrites_untouched_text(self):
        from tours.price_table_wording import GROUP_FROM, RATES, SLUG

        cat = Category.objects.create(name_en="Transfers", slug="transfers", is_transfer=True)
        exp = Experience.objects.create(
            category=cat, slug=SLUG, title_en="Airport", origin_en="NAT", destination_en="Pipa",
            important_info_pt="Valor por carro, para até 3 pessoas\nCarros de 7 lugares e grupos grandes: valor sob consulta",
            description_en="My own text written in the panel.")
        migration = import_module("tours.migrations.0010_airport_transfer_price_table")
        migration.forwards(django_apps, None)
        exp.refresh_from_db()
        self.assertEqual((exp.transfer_rates, exp.group_from), (RATES, GROUP_FROM))
        self.assertIn("6 pessoas: 2 carros, mais barato que uma van", exp.important_info_pt)
        self.assertEqual(exp.description_en, "My own text written in the panel.")


class TeamPricesMigrationTests(TestCase):
    def test_ponta_negra_table_and_fixed_speedboat(self):
        from importlib import import_module
        from django.apps import apps
        from bookings.forms import BookingRequestForm
        from tours.transfer_pricing import quote as make_quote
        m = import_module("tours.migrations.0016_ponta_negra_and_speedboat_prices")
        cat = Category.objects.create(name_en="Transfers", slug="tr", is_transfer=True)
        pn = Experience.objects.create(category=cat, slug=m.PONTA_NEGRA, title_en="PN", price=230,
                                       price_unit="vehicle", meta_description_pt="a partir de R$ 230 por carro")
        tours_cat = Category.objects.create(name_en="Tours", slug="tours-x")
        boat = Experience.objects.create(category=tours_cat, slug=m.SPEEDBOAT, title_en="Boat", price=70,
                                         price_unit="person", price_is_starting=True)
        m.forwards(apps, None)
        pn.refresh_from_db(); boat.refresh_from_db()
        self.assertEqual(pn.meta_description_pt, "a partir de R$ 210 por carro")
        q = make_quote(pn, 2)
        self.assertEqual(q.total, 210)
        self.assertTrue(make_quote(pn, 4).is_group)  # bigger groups: price on request
        self.assertFalse(boat.price_is_starting)
        self.assertEqual(BookingRequestForm._exact_total(boat, 3, None), 210)
