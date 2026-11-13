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
