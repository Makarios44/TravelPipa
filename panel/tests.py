"""Tests for the TravelPipa management panel (/gestao/)."""
import json
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from bookings.models import BookingRequest
from core.models import ContactMessage, SiteSettings, Testimonial
from tours.models import Category, Experience, ExperienceImage

TEMP_MEDIA = tempfile.mkdtemp()


def image_file(name="foto.jpg", size=(800, 600), color=(0, 127, 134)):
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=TEMP_MEDIA, PANEL_LOGIN_MAX_ATTEMPTS=3)
class PanelTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.staff = User.objects.create_user("equipe", "e@example.com", "Senha-forte-123", is_staff=True)
        self.customer = User.objects.create_user("cliente", "c@example.com", "Senha-forte-123")
        self.cat = Category.objects.create(name_en="Boat Experiences", name_pt="Passeios de barco",
                                           slug="boat-experiences")
        self.tour = Experience.objects.create(category=self.cat, title_en="Dolphin Bay Tour",
                                              title_pt="Passeio à Baía dos Golfinhos")
        self.client.force_login(self.staff)


class AccessTests(PanelTestCase):
    PAGES = ["panel:dashboard", "panel:experiences", "panel:experience_new", "panel:categories",
             "panel:category_new", "panel:bookings", "panel:messages", "panel:testimonials",
             "panel:testimonial_new", "panel:settings", "panel:password"]

    def test_all_pages_load_for_staff_in_portuguese(self):
        for name in self.PAGES:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
                self.assertContains(response, '<html lang="pt-br">')
        self.assertEqual(self.client.get(reverse("panel:experience_edit", args=[self.tour.pk])).status_code, 200)

    def test_anonymous_redirected_to_login(self):
        anon = Client()
        response = anon.get("/gestao/passeios/")
        self.assertRedirects(response, "/gestao/entrar/?next=/gestao/passeios/", fetch_redirect_response=False)
        response = anon.post(reverse("panel:experience_toggle", args=[self.tour.pk, "active"]))
        self.assertEqual(response.status_code, 302)
        self.tour.refresh_from_db()
        self.assertTrue(self.tour.active)

    def test_non_staff_cannot_enter(self):
        other = Client()
        response = other.post(reverse("panel:login"), {"username": "cliente", "password": "Senha-forte-123"})
        self.assertContains(response, "não tem acesso ao painel")
        other.force_login(self.customer)
        self.assertRedirects(other.get("/gestao/"), "/gestao/entrar/", fetch_redirect_response=False)

    def test_login_logout_and_next(self):
        anon = Client()
        response = anon.post("/gestao/entrar/?next=/gestao/reservas/",
                             {"username": "equipe", "password": "Senha-forte-123", "next": "/gestao/reservas/"})
        self.assertRedirects(response, "/gestao/reservas/", fetch_redirect_response=False)
        self.assertEqual(anon.get("/gestao/").status_code, 200)
        anon.post(reverse("panel:logout"))
        self.assertEqual(anon.get("/gestao/").status_code, 302)

    def test_login_rejects_external_next(self):
        anon = Client()
        response = anon.post(reverse("panel:login"), {"username": "equipe", "password": "Senha-forte-123",
                                                      "next": "https://evil.example.com/"})
        self.assertRedirects(response, "/gestao/", fetch_redirect_response=False)

    def test_login_locked_after_too_many_attempts(self):
        anon = Client()
        for _ in range(3):
            anon.post(reverse("panel:login"), {"username": "equipe", "password": "errada"})
        # Even the right password is refused while locked
        response = anon.post(reverse("panel:login"), {"username": "equipe", "password": "Senha-forte-123"})
        self.assertContains(response, "Muitas tentativas")
        self.assertEqual(anon.get("/gestao/").status_code, 302)

    def test_logout_requires_post(self):
        self.assertEqual(self.client.get(reverse("panel:logout")).status_code, 405)

    def test_csrf_enforced(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.staff)
        response = strict.post(reverse("panel:experience_toggle", args=[self.tour.pk, "active"]))
        self.assertEqual(response.status_code, 403)

    def test_password_change(self):
        response = self.client.post(reverse("panel:password"), {
            "old_password": "Senha-forte-123", "new_password1": "Nova-senha-pipa-2026",
            "new_password2": "Nova-senha-pipa-2026"})
        self.assertRedirects(response, "/gestao/", fetch_redirect_response=False)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password("Nova-senha-pipa-2026"))


class ExperienceTests(PanelTestCase):
    def test_toggle_active_and_featured(self):
        url = reverse("panel:experience_toggle", args=[self.tour.pk, "active"])
        response = self.client.post(url, {"value": "0"}, headers={"X-Requested-With": "fetch"})
        self.assertEqual(json.loads(response.content)["value"], False)
        self.tour.refresh_from_db()
        self.assertFalse(self.tour.active)
        self.assertEqual(self.client.get("/en/experiences/dolphin-bay-tour/").status_code, 404)
        self.client.post(url)  # without JavaScript: flips the value
        self.tour.refresh_from_db()
        self.assertTrue(self.tour.active)
        self.client.post(reverse("panel:experience_toggle", args=[self.tour.pk, "featured"]), {"value": "1"})
        self.tour.refresh_from_db()
        self.assertTrue(self.tour.featured)
        self.assertEqual(self.client.post(reverse("panel:experience_toggle", args=[self.tour.pk, "price"])).status_code, 400)

    def _form_data(self, **extra):
        data = {"category": self.cat.pk, "slug": "", "order": 0, "active": "on", "currency": "BRL",
                "price_unit": "person", "price_is_starting": "on", "title_en": "Sunset Cruise",
                "title_pt": "Passeio ao pôr do sol", "title_es": "Paseo al atardecer", "price": "150",
                "included_pt": "Barco\nColetes"}
        data.update(extra)
        return data

    def test_create_and_edit_experience(self):
        response = self.client.post(reverse("panel:experience_new"), self._form_data())
        exp = Experience.objects.get(title_en="Sunset Cruise")
        self.assertRedirects(response, reverse("panel:experience_edit", args=[exp.pk]), fetch_redirect_response=False)
        self.assertEqual(exp.slug, "sunset-cruise")
        self.assertEqual(exp.included_list if False else exp.included_pt.splitlines(), ["Barco", "Coletes"])
        response = self.client.post(reverse("panel:experience_edit", args=[exp.pk]),
                                    self._form_data(price="180", slug=exp.slug, active=""))
        exp.refresh_from_db()
        self.assertEqual(exp.price, 180)
        self.assertFalse(exp.active)

    def test_validation_errors_are_shown(self):
        response = self.client.post(reverse("panel:experience_new"), self._form_data(title_en=""))
        self.assertContains(response, "Confira os campos destacados")
        self.assertContains(response, "is-invalid")
        transfer_cat = Category.objects.create(name_en="Transfers", slug="transfers", is_transfer=True)
        response = self.client.post(reverse("panel:experience_new"), self._form_data(category=transfer_cat.pk))
        self.assertContains(response, "origem e o destino")

    def test_delete_experience_keeps_bookings(self):
        booking = BookingRequest.objects.create(experience=self.tour, preferred_date=timezone.localdate(),
                                                people=2, full_name="Ana", email="a@example.com", phone="+5584999999999")
        self.assertContains(self.client.get(reverse("panel:experience_delete", args=[self.tour.pk])), "Sim, excluir")
        self.client.post(reverse("panel:experience_delete", args=[self.tour.pk]))
        self.assertFalse(Experience.objects.filter(pk=self.tour.pk).exists())
        booking.refresh_from_db()
        self.assertEqual(booking.experience_title, "Dolphin Bay Tour")

    def test_list_filters(self):
        Experience.objects.create(category=self.cat, title_en="Hidden", active=False)
        response = self.client.get(reverse("panel:experiences"), {"show": "inactive"})
        self.assertContains(response, "Hidden")
        self.assertNotContains(response, "Baía dos Golfinhos")
        self.assertContains(self.client.get(reverse("panel:experiences"), {"q": "golfinhos"}), "Baía dos Golfinhos")


class PhotoTests(PanelTestCase):
    def upload(self, *files):
        return self.client.post(reverse("panel:photo_upload", args=[self.tour.pk]), {"photos": list(files)})

    def test_upload_several_photos_first_becomes_cover(self):
        self.upload(image_file("a.jpg"), image_file("b.jpg"), image_file("c.jpg"))
        photos = list(self.tour.images.order_by("order"))
        self.assertEqual(len(photos), 3)
        self.assertTrue(photos[0].is_cover)
        self.assertEqual([p.order for p in photos], [0, 1, 2])
        self.upload(image_file("d.jpg"))
        self.assertEqual(self.tour.images.filter(is_cover=True).count(), 1)
        self.assertEqual(self.tour.images.order_by("-order").first().order, 3)

    def test_rejects_non_images(self):
        fake = SimpleUploadedFile("virus.jpg", b"not an image", content_type="image/jpeg")
        self.upload(fake)
        self.assertEqual(self.tour.images.count(), 0)
        pdf = SimpleUploadedFile("doc.pdf", b"%PDF-1.4", content_type="application/pdf")
        self.upload(pdf)
        self.assertEqual(self.tour.images.count(), 0)

    def test_cover_reorder_alt_and_delete(self):
        self.upload(image_file("a.jpg"), image_file("b.jpg"), image_file("c.jpg"))
        a, b, c = self.tour.images.order_by("order")
        url = lambda photo, action: reverse("panel:photo_action", args=[self.tour.pk, photo.pk, action])
        self.client.post(url(c, "cover"))
        self.assertEqual(self.tour.images.get(is_cover=True), c)
        self.client.post(url(c, "up"))
        self.assertEqual(list(self.tour.images.order_by("order").values_list("pk", flat=True)), [a.pk, c.pk, b.pk])
        response = self.client.post(reverse("panel:photo_reorder", args=[self.tour.pk]),
                                    json.dumps({"order": [b.pk, a.pk, c.pk]}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(self.tour.images.order_by("order").values_list("pk", flat=True)), [b.pk, a.pk, c.pk])
        bad = self.client.post(reverse("panel:photo_reorder", args=[self.tour.pk]),
                               json.dumps({"order": [b.pk]}), content_type="application/json")
        self.assertEqual(bad.status_code, 400)
        self.client.post(url(a, "alt"), {f"p{a.pk}-alt_pt": "Golfinhos", f"p{a.pk}-alt_en": "Dolphins",
                                         f"p{a.pk}-alt_es": "Delfines"})
        a.refresh_from_db()
        self.assertEqual(a.alt_en, "Dolphins")
        self.client.post(url(c, "delete"))  # deleting the cover promotes another photo
        self.assertEqual(self.tour.images.count(), 2)
        self.assertEqual(self.tour.images.filter(is_cover=True).count(), 1)

    def test_inside_album(self):
        self.upload(image_file("byd.jpg"), image_file("painel.jpg"), image_file("banco.jpg"))
        byd, painel, banco = self.tour.images.order_by("order")
        url = lambda photo, action: reverse("panel:photo_action", args=[self.tour.pk, photo.pk, action])
        for photo in (painel, banco):
            self.client.post(url(photo, "alt"), {f"p{photo.pk}-album": "inside", f"p{photo.pk}-alt_pt": "Interior"})
        self.tour.refresh_from_db()
        self.assertEqual(self.tour.gallery, [byd])
        self.assertEqual(self.tour.inside_gallery, [painel, banco])
        self.assertEqual(self.tour.cover, byd)
        # Moving the cover into the album hands the cover to a main-gallery photo
        self.client.post(url(painel, "alt"), {f"p{painel.pk}-album": ""})
        self.client.post(url(byd, "alt"), {f"p{byd.pk}-album": "inside"})
        byd.refresh_from_db()
        self.assertFalse(byd.is_cover)
        self.assertEqual(self.tour.images.get(is_cover=True), painel)
        # "Set as cover" brings a photo back to the main gallery
        self.client.post(url(banco, "cover"))
        banco.refresh_from_db()
        self.assertEqual((banco.album, banco.is_cover), ("", True))

    def test_cannot_touch_photos_of_another_tour(self):
        other = Experience.objects.create(category=self.cat, title_en="Other")
        photo = ExperienceImage.objects.create(experience=other, image=image_file())
        response = self.client.post(reverse("panel:photo_action", args=[self.tour.pk, photo.pk, "delete"]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ExperienceImage.objects.filter(pk=photo.pk).exists())


class OtherSectionsTests(PanelTestCase):
    def test_category_toggle_and_edit(self):
        self.client.post(reverse("panel:category_toggle", args=[self.cat.pk]))
        self.cat.refresh_from_db()
        self.assertFalse(self.cat.active)
        self.client.post(reverse("panel:category_edit", args=[self.cat.pk]), {
            "name_pt": "Barco", "name_en": "Boat", "name_es": "Barco", "slug": "boat-experiences",
            "order": 1, "active": "on"})
        self.cat.refresh_from_db()
        self.assertEqual((self.cat.name_en, self.cat.active), ("Boat", True))

    def test_booking_flow(self):
        booking = BookingRequest.objects.create(experience=self.tour, preferred_date=timezone.localdate(),
                                                people=3, full_name="María López", email="m@example.com",
                                                phone="+54 9 11 5555-1234", service_language="es")
        response = self.client.get(reverse("panel:booking_detail", args=[booking.pk]))
        self.assertContains(response, "https://wa.me/5491155551234?text=Hola")
        self.assertContains(self.client.get(reverse("panel:dashboard")), booking.reference)
        self.client.post(reverse("panel:booking_detail", args=[booking.pk]),
                         {"status": "contacted", "internal_notes": "Respondido no WhatsApp"})
        booking.refresh_from_db()
        self.assertEqual(booking.status, "contacted")
        self.assertEqual(booking.full_name, "María López")
        self.assertContains(self.client.get(reverse("panel:bookings"), {"status": "contacted"}), booking.reference)
        self.assertNotContains(self.client.get(reverse("panel:bookings"), {"status": "pending"}), booking.reference)
        self.assertContains(self.client.get(reverse("panel:bookings"), {"q": "lópez"}), booking.reference)

    def test_messages(self):
        msg = ContactMessage.objects.create(name="Tom", email="t@example.com", message="Hello")
        self.assertContains(self.client.get(reverse("panel:messages")), "Hello")
        self.client.post(reverse("panel:message_toggle", args=[msg.pk]))
        msg.refresh_from_db()
        self.assertTrue(msg.handled)
        self.assertNotContains(self.client.get(reverse("panel:messages")), "Hello")

    def test_testimonials(self):
        self.client.post(reverse("panel:testimonial_new"), {
            "author_name": "Lucía", "text_es": "¡Excelente!", "confirmed_real": "on", "active": "on", "order": 0})
        t = Testimonial.objects.get()
        self.assertContains(self.client.get("/es/"), "¡Excelente!")
        self.client.post(reverse("panel:testimonial_delete", args=[t.pk]))
        self.assertFalse(Testimonial.objects.exists())

    def test_site_settings_update_reaches_the_site(self):
        response = self.client.post(reverse("panel:settings"), {
            "site_name": "TravelPipa", "whatsapp": "+55 84 98888-7777", "email": "ola@travelpipa.com",
            "trust_der_vehicles": "on", "hero_image": image_file("banner.jpg", size=(1600, 900))})
        self.assertRedirects(response, reverse("panel:settings"), fetch_redirect_response=False)
        site = SiteSettings.load()
        self.assertEqual(site.whatsapp, "+55 84 98888-7777")
        self.assertFalse(site.trust_cadastur_guides)
        self.assertTrue(site.hero_image)
        home = self.client.get("/en/")
        self.assertContains(home, "wa.me/5584988887777")
        self.assertContains(home, site.hero_image.url)
        bad = self.client.post(reverse("panel:settings"), {"site_name": "TravelPipa", "whatsapp": "123"})
        self.assertContains(bad, "código do país")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_ENABLED=True)
class DriverDetailsTests(PanelTestCase):
    def setUp(self):
        super().setUp()
        SiteSettings.objects.update_or_create(pk=1, defaults={"email": "contato@travelpipa.com.br"})
        self.booking = BookingRequest.objects.create(
            experience=self.tour, preferred_date=timezone.localdate(), people=2, full_name="Ana Souza",
            email="ana@example.com", phone="+55 84 99999-9999", service_language="pt-br")
        self.url = reverse("panel:booking_detail", args=[self.booking.pk])

    def data(self, **extra):
        return {"form": "driver", "drv-driver_name": "Damião", "drv-vehicle_model": "BYD Song Pro branco",
                "drv-vehicle_plate": "tov 8h80", **extra}

    def test_save_shows_whatsapp_and_preview(self):
        from django.core import mail
        self.client.post(self.url, self.data(action="save"))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.vehicle_plate, "TOV8H80")
        self.assertIsNone(self.booking.driver_sent_at)
        self.assertEqual(len(mail.outbox), 0)
        page = self.client.get(self.url)
        self.assertContains(page, "Enviar pelo WhatsApp")
        self.assertContains(page, "Placa: TOV8H80")
        self.assertNotContains(page, "Veículo cadastrado no DER/RN para")  # not ticked

    def test_email_with_photos_in_customer_language(self):
        from django.core import mail
        self.client.post(self.url, self.data(**{"action": "email", "drv-vehicle_der": "on",
                                                "drv-driver_photo": image_file("d.jpg"),
                                                "drv-vehicle_photo": image_file("c.jpg")}))
        self.booking.refresh_from_db()
        self.assertIsNotNone(self.booking.driver_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["ana@example.com"])
        self.assertEqual(email.reply_to, ["contato@travelpipa.com.br"])
        self.assertIn("Seu motorista", email.subject)
        self.assertIn("Motorista: Damião", email.body)
        self.assertIn("Placa: TOV8H80", email.body)
        self.assertIn("DER/RN", email.body)
        self.assertEqual(sorted(a[0].split(".")[0] for a in email.attachments), ["carro", "motorista"])
        self.assertContains(self.client.get(reverse("panel:bookings")), "Motorista enviado")

    def test_needs_name_and_plate_to_email(self):
        from django.core import mail
        self.client.post(self.url, {"form": "driver", "action": "email", "drv-driver_name": "Damião"})
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_plate(self):
        response = self.client.post(self.url, self.data(**{"drv-vehicle_plate": "12", "action": "save"}))
        self.assertContains(response, "Placa inválida")

    def test_status_form_still_works(self):
        self.client.post(self.url, {"status": "confirmed", "internal_notes": "ok"})
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "confirmed")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_ENABLED=True,
                   SITE_URL="https://travelpipa.com.br")
class VoucherTests(PanelTestCase):
    def setUp(self):
        super().setUp()
        from decimal import Decimal
        self.booking = BookingRequest.objects.create(
            experience=self.tour, preferred_date=timezone.localdate() + timezone.timedelta(days=3), people=3,
            full_name="Raphael Lima", email="r@example.com", phone="+55 84 98888-7777", service_language="pt-br",
            status="confirmed", deposit_amount=Decimal("24"), driver_name="Rodrigo Tavares",
            vehicle_model="Nissan Sentra", vehicle_plate="PLZ2E15", driver_phone="84 99999-0000")
        self.url = reverse("panel:booking_detail", args=[self.booking.pk])

    def fill(self, **extra):
        data = {"form": "voucher", "action": "save", "vch-pickup_time": "14:30",
                "vch-pickup_place": "Aeroporto de Natal", "vch-dropoff_place": "Pousada Sol, Pipa",
                "vch-total_price": "240", "vch-deposit_received": "24", **extra}
        return self.client.post(self.url, data)

    def test_amounts_and_both_vouchers(self):
        from decimal import Decimal
        self.fill()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.amount_due, Decimal("216"))
        page = self.client.get(self.url)
        self.assertContains(page, "Ver voucher do cliente")
        self.assertContains(page, "Enviar ao motorista pelo WhatsApp")
        self.assertContains(page, "wa.me/5584999990000")
        self.client.logout()
        client_page = self.client.get(reverse("voucher", args=[self.booking.uuid]))
        self.assertContains(client_page, "Sinal pago")
        self.assertContains(client_page, "R$ 216")
        self.assertContains(client_page, "PLZ2E15")
        self.assertNotContains(client_page, "COBRAR")
        self.assertEqual(client_page["X-Robots-Tag"], "noindex, nofollow")
        self.booking.refresh_from_db()
        driver_page = self.client.get(reverse("driver_voucher", args=[self.booking.driver_token]))
        self.assertContains(driver_page, "Cobrar do cliente no dia")
        self.assertContains(driver_page, "R$ 216")
        self.assertContains(driver_page, "R$ 240")
        self.assertContains(driver_page, "+55 84 98888-7777")

    def test_customer_voucher_in_english(self):
        self.booking.service_language = "en"
        self.booking.save()
        self.fill()
        page = self.client.get(reverse("voucher", args=[self.booking.uuid]))
        self.assertContains(page, "Left to pay on the day")
        self.assertContains(page, "Deposit paid")

    def test_email_to_customer(self):
        from django.core import mail
        self.fill(action="email")
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("Restante a pagar no dia: R$ 216", body)
        self.assertIn(f"https://travelpipa.com.br/voucher/{self.booking.uuid}/", body)

    def test_not_ready_until_confirmed_and_filled(self):
        self.booking.status = "contacted"
        self.booking.save()
        page = self.client.get(self.url)
        self.assertContains(page, "Para gerar os vouchers, falta")
        self.client.logout()
        self.assertEqual(self.client.get(reverse("voucher", args=[self.booking.uuid])).status_code, 404)

    def test_mercadopago_deposit_counts(self):
        from decimal import Decimal
        BookingRequest.objects.filter(pk=self.booking.pk).update(payment_status="paid", paid_amount=Decimal("24"))
        self.fill(**{"vch-deposit_received": ""})
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.amount_due, Decimal("216"))

    def test_deposit_bigger_than_total(self):
        response = self.fill(**{"vch-deposit_received": "300"})
        self.assertContains(response, "não pode ser maior")

    def test_trip_list(self):
        self.fill()
        page = self.client.get(reverse("panel:trips"))
        self.assertContains(page, "14:30")
        self.assertContains(page, "Rodrigo Tavares")
        self.assertContains(page, "a cobrar")
        self.assertNotContains(self.client.get(reverse("panel:trips") + "?when=past"), "Rodrigo")

    def test_expired_voucher(self):
        self.fill()
        BookingRequest.objects.filter(pk=self.booking.pk).update(
            preferred_date=timezone.localdate() - timezone.timedelta(days=40))
        self.assertEqual(self.client.get(reverse("voucher", args=[self.booking.uuid])).status_code, 404)
