from decimal import Decimal

from django.test import TestCase

from bookings.forms import BookingRequestForm as BookingForm, vehicle_summary
from bookings.mercadopago import deposit_for
from tours.models import Category, Experience


class PerVehiclePriceTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name_en="Tours", slug="tours")
        self.quad = Experience.objects.create(category=cat, slug="quad", title_en="Quad", price=Decimal("200"),
                                              price_unit="vehicle", price_is_starting=False, people_per_vehicle=2)

    def test_group_pays_for_every_vehicle(self):
        self.assertEqual(BookingForm._exact_total(self.quad, 1, None), Decimal("200"))
        self.assertEqual(BookingForm._exact_total(self.quad, 2, None), Decimal("200"))
        self.assertEqual(BookingForm._exact_total(self.quad, 3, None), Decimal("400"))
        self.assertEqual(deposit_for(BookingForm._exact_total(self.quad, 4, None)), Decimal("40.00"))
        self.assertEqual(vehicle_summary(self.quad, 3), "2 veículos × R$ 200 = R$ 400 (3 pessoas)")

    def test_unknown_capacity_leaves_the_deposit_to_the_team(self):
        self.quad.people_per_vehicle = None
        self.assertIsNone(BookingForm._exact_total(self.quad, 4, None))
        self.assertEqual(vehicle_summary(self.quad, 4), "")
