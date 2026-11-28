from decimal import Decimal

from django.test import TestCase, override_settings

from tours.models import Category, Experience


@override_settings(MERCADOPAGO_ACCESS_TOKEN="APP_USR-123")
class DepositTextsTests(TestCase):
    def setUp(self):
        transfers = Category.objects.create(name_en="Transfers", name_pt="Transfers", slug="transfers",
                                            is_transfer=True)
        tours = Category.objects.create(name_en="Tours", name_pt="Passeios", slug="tours")
        self.transfer = Experience.objects.create(
            category=transfers, slug="pn", title_en="PN", title_pt="Transfer PN", price=Decimal("210"),
            price_unit="vehicle", transfer_rates="3: 210", group_from=4, active=True)
        self.boat = Experience.objects.create(
            category=tours, slug="boat", title_en="Boat", title_pt="Lancha", price=Decimal("70"),
            price_unit="person", price_is_starting=False, active=True)
        self.gastro = Experience.objects.create(
            category=tours, slug="gastro", title_en="Gastro", title_pt="Gastro", price=Decimal("325"),
            price_unit="person", price_is_starting=True, active=True)

    def get(self, exp):
        return self.client.get(exp.get_absolute_url().replace("/en/", "/pt-br/", 1)
                               if exp.get_absolute_url().startswith("/en/") else exp.get_absolute_url())

    def test_detail_pages_show_the_deposit(self):
        from django.utils import translation
        with translation.override("pt-br"):
            transfer_url, boat_url, gastro_url = (e.get_absolute_url() for e in (self.transfer, self.boat, self.gastro))
        self.assertContains(self.client.get(transfer_url),
                            "Ao confirmar a reserva, você paga um sinal de 10% por Pix (a partir de R$ 21)")
        self.assertContains(self.client.get(boat_url), "(R$ 7 por pessoa)")
        gastro = self.client.get(gastro_url)
        self.assertContains(gastro, "entramos em contato o mais rápido possível com o valor")
        self.assertNotContains(gastro, "sem pagar nada")

    def test_booking_form_and_terms_in_portuguese(self):
        form = self.client.get("/pt-br/reservar/")
        self.assertContains(form, "Garanta sua data com um sinal de 10%.")
        self.assertContains(form, "Sinal (10%) por Pix ao confirmar: {amount}")
        self.assertContains(form, 'data-price="70.00"')
        self.assertNotContains(form, "sem pagar nada")
        self.assertContains(self.client.get("/pt-br/termos-e-condicoes/"), "Para garantir a reserva pedimos um sinal de 10%")

    @override_settings(MERCADOPAGO_ACCESS_TOKEN="")
    def test_without_online_payment_keeps_the_old_flow(self):
        form = self.client.get("/pt-br/reservar/")
        self.assertNotContains(form, "data-deposit-box")
        self.assertContains(form, "Reserve em poucos minutos.")
