"""Deposit paid online with Mercado Pago Checkout Pro (all Mercado Pago answers are simulated)."""
import datetime
import hashlib
import hmac
import json
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from bookings import mercadopago
from bookings.models import BookingRequest
from core.tests import BaseTestCase

MP = override_settings(MERCADOPAGO_ACCESS_TOKEN="APP_USR-test-token", MERCADOPAGO_WEBHOOK_SECRET="")
MAIL = override_settings(EMAIL_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                         NOTIFICATION_EMAILS=["team@example.com"])
PREFERENCE = {"id": "pref-123", "init_point": "https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=pref-123",
              "sandbox_init_point": "https://sandbox.mercadopago.com.br/checkout/v1/redirect?pref_id=pref-123"}


def payment(booking, status="approved", amount="46.00", currency="BRL", pid=987654321):
    return {"id": pid, "status": status, "transaction_amount": float(amount), "currency_id": currency,
            "external_reference": str(booking.uuid)}


@MP
class DepositTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.transfer.transfer_rates = "3: 240 / 230\n4: 280 / 270\n5: 300 / 290"
        self.transfer.group_from = 7
        self.transfer.price = Decimal("240")
        self.transfer.save()

    def book(self, **extra):
        day = (timezone.localdate() + datetime.timedelta(days=15)).isoformat()
        data = self.booking_payload(experience=self.transfer.pk, trip_type="round_trip", return_date=day, **extra)
        self.client.post(reverse("bookings:request"), data)
        return BookingRequest.objects.latest("created_at")

    # --- amount ------------------------------------------------------------------
    def test_deposit_is_ten_percent_of_an_exact_total(self):
        booking = self.book()
        self.assertEqual((booking.quoted_total, booking.deposit_amount), (Decimal("460.00"), Decimal("46.00")))
        group = self.book(people=9, email="g@example.com")
        self.assertIsNone(group.deposit_amount)

    def test_tours_only_get_a_deposit_with_a_closed_price(self):
        self.boat.price, self.boat.price_is_starting, self.boat.price_unit = Decimal("150"), False, "person"
        self.boat.save()
        self.client.post(reverse("bookings:request"), self.booking_payload(people=3))
        self.assertEqual(BookingRequest.objects.get().deposit_amount, Decimal("45.00"))
        self.boat.price_is_starting = True
        self.boat.save()
        self.client.post(reverse("bookings:request"), self.booking_payload(people=3, email="x@example.com"))
        self.assertIsNone(BookingRequest.objects.latest("created_at").deposit_amount)

    def test_thanks_page_offers_the_deposit_only_when_configured(self):
        booking = self.book()
        page = self.client.get(reverse("bookings:thanks"))
        self.assertContains(page, reverse("bookings:deposit", args=[booking.uuid]))
        self.assertContains(page, "Pay the deposit (R$ 46)")
        with override_settings(MERCADOPAGO_ACCESS_TOKEN=""):
            self.assertNotContains(self.client.get(reverse("bookings:thanks")), "Pay the deposit")

    # --- preference ----------------------------------------------------------------
    def test_deposit_page_creates_the_checkout_once(self):
        booking = self.book()
        url = reverse("bookings:deposit", args=[booking.uuid])
        with mock.patch.object(mercadopago, "_call", return_value=PREFERENCE) as call:
            page = self.client.get(url)
            self.client.get(url)
        self.assertEqual(call.call_count, 1)
        method, path, body = call.call_args.args[:3]
        self.assertEqual((method, path), ("POST", "/checkout/preferences"))
        self.assertEqual(body["items"][0]["unit_price"], 46.0)
        self.assertEqual(body["items"][0]["currency_id"], "BRL")
        self.assertEqual(body["external_reference"], str(booking.uuid))
        self.assertTrue(body["notification_url"].endswith("/pagamentos/mercadopago/"))
        self.assertTrue(body["back_urls"]["success"].endswith(url))
        self.assertContains(page, PREFERENCE["init_point"].replace("&", "&amp;"))
        self.assertEqual(page["X-Robots-Tag"], "noindex, nofollow")
        booking.refresh_from_db()
        self.assertEqual((booking.payment_status, booking.mp_preference_id), ("waiting", "pref-123"))

    @override_settings(MERCADOPAGO_ACCESS_TOKEN="TEST-123")
    def test_test_credentials_use_the_sandbox_link(self):
        booking = self.book()
        with mock.patch.object(mercadopago, "_call", return_value=PREFERENCE):
            page = self.client.get(reverse("bookings:deposit", args=[booking.uuid]))
        self.assertContains(page, "sandbox.mercadopago.com.br")

    def test_mercado_pago_down_shows_a_friendly_message(self):
        booking = self.book()
        with mock.patch.object(mercadopago, "_call", side_effect=mercadopago.MercadoPagoError("down")):
            page = self.client.get(reverse("bookings:deposit", args=[booking.uuid]))
        self.assertContains(page, "could not open the payment page")

    # --- confirmation --------------------------------------------------------------
    @MAIL
    def test_webhook_marks_paid_after_asking_mercado_pago(self):
        booking = self.book()
        mail.outbox.clear()
        with mock.patch.object(mercadopago, "_call", return_value=payment(booking)) as call:
            response = self.client.post("/pagamentos/mercadopago/", data=json.dumps(
                {"type": "payment", "data": {"id": "987654321"}}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        call.assert_called_once_with("GET", "/v1/payments/987654321")
        booking.refresh_from_db()
        self.assertEqual((booking.payment_status, booking.paid_amount, booking.mp_payment_id),
                         ("paid", Decimal("46.00"), "987654321"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Sinal pago", mail.outbox[0].subject)
        # Same notification again: no second e-mail.
        with mock.patch.object(mercadopago, "_call", return_value=payment(booking)):
            self.client.post("/pagamentos/mercadopago/?type=payment&data.id=987654321")
        self.assertEqual(len(mail.outbox), 1)
        page = self.client.get(reverse("bookings:deposit", args=[booking.uuid]))
        self.assertContains(page, "Deposit paid. Your date is secured!")

    def test_short_or_foreign_payments_are_not_marked_paid(self):
        booking = self.book()
        for data in (payment(booking, amount="10.00"), payment(booking, currency="USD")):
            with mock.patch.object(mercadopago, "_call", return_value=data):
                mercadopago.sync_payment("1")
            booking.refresh_from_db()
            self.assertEqual(booking.payment_status, "in_process")

    def test_a_later_failed_attempt_does_not_undo_a_paid_deposit(self):
        booking = self.book()
        with mock.patch.object(mercadopago, "_call", return_value=payment(booking)):
            mercadopago.sync_payment("1")
        with mock.patch.object(mercadopago, "_call", return_value=payment(booking, status="rejected", pid=2)):
            mercadopago.sync_payment("2")
        booking.refresh_from_db()
        self.assertEqual((booking.payment_status, booking.mp_payment_id), ("paid", "1"))

    def test_return_page_checks_the_payment_and_ignores_other_bookings(self):
        booking = self.book()
        other = self.book(email="other@example.com")
        url = reverse("bookings:deposit", args=[booking.uuid])
        with mock.patch.object(mercadopago, "_call", side_effect=[payment(other), PREFERENCE]):
            self.client.get(url + "?payment_id=555&status=approved")
        booking.refresh_from_db()
        self.assertNotEqual(booking.payment_status, "paid")
        with mock.patch.object(mercadopago, "_call", return_value=payment(booking)):
            page = self.client.get(url + "?payment_id=556&status=approved")
        self.assertContains(page, "Deposit paid")

    def test_webhook_errors_and_other_topics(self):
        self.assertEqual(self.client.post("/pagamentos/mercadopago/", data="not json",
                                          content_type="application/json").status_code, 200)
        self.assertEqual(self.client.post("/pagamentos/mercadopago/?topic=merchant_order&id=1").status_code, 200)
        with mock.patch.object(mercadopago, "_call", side_effect=mercadopago.MercadoPagoError("down")):
            response = self.client.post("/pagamentos/mercadopago/?type=payment&data.id=1")
        self.assertEqual(response.status_code, 502)  # Mercado Pago will try again

    def test_webhook_signature_when_a_secret_is_set(self):
        booking = self.book()
        url = "/pagamentos/mercadopago/?type=payment&data.id=777"
        with override_settings(MERCADOPAGO_WEBHOOK_SECRET="s3cret"):
            bad = self.client.post(url, headers={"x-signature": "ts=1,v1=abc", "x-request-id": "r1"})
            self.assertEqual(bad.status_code, 401)
            sig = hmac.new(b"s3cret", b"id:777;request-id:r1;ts:1;", hashlib.sha256).hexdigest()
            with mock.patch.object(mercadopago, "_call", return_value=payment(booking, pid=777)):
                good = self.client.post(url, headers={"x-signature": f"ts=1,v1={sig}", "x-request-id": "r1"})
        self.assertEqual(good.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.payment_status, "paid")

    # --- panel ---------------------------------------------------------------------
    def test_panel_shows_link_and_resets_it_when_the_amount_changes(self):
        booking = self.book()
        booking.mp_init_point, booking.payment_status = PREFERENCE["init_point"], "waiting"
        booking.save()
        staff = get_user_model().objects.create_user("equipe", "e@example.com", "Senha-forte-123", is_staff=True)
        self.client.force_login(staff)
        url = reverse("panel:booking_detail", args=[booking.pk])
        page = self.client.get(url)
        self.assertContains(page, "Enviar link do sinal")
        self.assertContains(page, f"/en/book/deposit/{booking.uuid}/")  # in the customer's language
        self.client.post(url, {"status": "contacted", "deposit_amount": "60.00", "internal_notes": ""})
        booking.refresh_from_db()
        self.assertEqual((booking.deposit_amount, booking.mp_init_point, booking.payment_status),
                         (Decimal("60.00"), "", ""))
