"""
End-to-end tests for the TravelPipa MVP.

Run with:  python manage.py test
"""
import datetime
import shutil
import tempfile
from io import BytesIO, StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone, translation
from PIL import Image

from bookings.models import BookingRequest
from core.models import SiteSettings, Testimonial
from tours.models import Category, Experience, ExperienceImage

TEMP_MEDIA = tempfile.mkdtemp()


def make_image(name="photo.jpg", size=(2400, 1600)):
    buffer = BytesIO()
    Image.new("RGB", size, (0, 127, 134)).save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=TEMP_MEDIA, FORM_MIN_FILL_SECONDS=0, FORM_RATE_LIMIT_PER_HOUR=100, SITE_URL="")
class BaseTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()
        translation.activate("en")
        self.addCleanup(translation.deactivate)
        self.boats = Category.objects.create(name_en="Boat Experiences", name_pt="Passeios de barco",
                                             name_es="Paseos en barco", slug="boat-experiences", order=1)
        self.transfers_cat = Category.objects.create(name_en="Transfers", name_es="Traslados", slug="transfers",
                                                     is_transfer=True, order=5)
        self.boat = Experience.objects.create(
            category=self.boats, title_en="Dolphin Bay Boat Tour", title_pt="Passeio à Baía dos Golfinhos",
            title_es="Paseo a la Bahía de los Delfines", summary_en="Sail along the cliffs.",
            description_en="First paragraph.\n\nSecond paragraph.", included_en="Boat ride\nLife jackets",
            not_included_en="Drinks", itinerary_en="Meet\nSail\nReturn", featured=True,
        )
        self.transfer = Experience.objects.create(
            category=self.transfers_cat, title_en="Natal Airport to Pipa", title_pt="Aeroporto de Natal para Pipa",
            origin_en="Natal Airport", origin_pt="Aeroporto de Natal", destination_en="Pipa",
            transfer_type="private", max_passengers=4,
        )

    def booking_payload(self, **overrides):
        data = {
            "experience": self.boat.pk,
            "preferred_date": (timezone.localdate() + datetime.timedelta(days=10)).isoformat(),
            "people": 2,
            "full_name": "Maria Silva",
            "email": "maria@example.com",
            "phone": "+44 7700 900123",
            "service_language": "en",
            "notes": "Staying in the village centre.",
            "consent": "on",
            "website": "",
        }
        page = self.client.get(reverse("bookings:request"))
        data["form_ts"] = page.context["form"].initial["form_ts"]
        data.update(overrides)
        return data


class ModelTests(BaseTestCase):
    def test_localized_fields_follow_active_language_with_english_fallback(self):
        with translation.override("pt-br"):
            self.assertEqual(self.boat.title, "Passeio à Baía dos Golfinhos")
            self.assertEqual(self.boat.summary, "Sail along the cliffs.")  # fallback to English
        with translation.override("es"):
            self.assertEqual(self.boat.title, "Paseo a la Bahía de los Delfines")
            self.assertEqual(self.transfer.origin, "Natal Airport")

    def test_slug_is_generated_and_unique(self):
        self.assertEqual(self.boat.slug, "dolphin-bay-boat-tour")
        other = Experience.objects.create(category=self.boats, title_en="Dolphin Bay Boat Tour")
        self.assertEqual(other.slug, "dolphin-bay-boat-tour-2")

    def test_list_helpers(self):
        self.assertEqual(self.boat.included_list, ["Boat ride", "Life jackets"])
        self.assertEqual(len(self.boat.description_paragraphs), 2)

    def test_published_excludes_inactive_experiences_and_categories(self):
        self.assertIn(self.boat, Experience.objects.published())
        self.boat.active = False
        self.boat.save()
        self.assertNotIn(self.boat, Experience.objects.published())
        self.transfers_cat.active = False
        self.transfers_cat.save()
        self.assertNotIn(self.transfer, Experience.objects.published())

    def test_booking_reference_is_unique_and_status_pending(self):
        a = BookingRequest.objects.create(experience=self.boat, preferred_date=timezone.localdate(), people=2,
                                          full_name="A", email="a@example.com", phone="+5584999999999")
        b = BookingRequest.objects.create(experience=self.boat, preferred_date=timezone.localdate(), people=2,
                                          full_name="B", email="b@example.com", phone="+5584999999999")
        self.assertRegex(a.reference, r"^TP-[A-Z2-9]{7}$")
        self.assertNotEqual(a.reference, b.reference)
        self.assertNotEqual(a.uuid, b.uuid)
        self.assertEqual(a.status, BookingRequest.Status.PENDING)
        self.assertEqual(a.experience_title, "Dolphin Bay Boat Tour")
        self.assertIsNotNone(a.created_at)

    def test_booking_survives_experience_deletion(self):
        b = BookingRequest.objects.create(experience=self.boat, preferred_date=timezone.localdate(), people=1,
                                          full_name="A", email="a@example.com", phone="+5584999999999")
        self.boat.delete()
        b.refresh_from_db()
        self.assertIsNone(b.experience)
        self.assertEqual(b.experience_title, "Dolphin Bay Boat Tour")

    def test_site_settings_is_singleton(self):
        SiteSettings.load()
        SiteSettings(site_name="Other").save()
        self.assertEqual(SiteSettings.objects.count(), 1)
        SiteSettings.load().delete()
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_uploaded_images_are_resized(self):
        img = ExperienceImage(experience=self.boat, image=make_image(size=(4000, 2000)), is_cover=True)
        img.save()
        img.refresh_from_db()
        self.assertLessEqual(max(img.width, img.height), 2560)
        self.assertEqual(self.boat.cover, img)

    def test_reasonable_images_are_kept_byte_for_byte(self):
        upload = make_image(size=(1600, 1200))
        original = upload.read()
        upload.seek(0)
        img = ExperienceImage.objects.create(experience=self.boat, image=upload)
        with img.image.open("rb") as fh:
            self.assertEqual(fh.read(), original)


class PublicPagesTests(BaseTestCase):
    URLS = {
        "en": ["/en/", "/en/experiences/", "/en/experiences/dolphin-bay-boat-tour/", "/en/transfers/",
               "/en/about/", "/en/contact/", "/en/book/", "/en/privacy-policy/", "/en/terms-and-conditions/"],
        "pt-br": ["/pt-br/", "/pt-br/passeios/", "/pt-br/passeios/dolphin-bay-boat-tour/", "/pt-br/transfers/",
                  "/pt-br/sobre/", "/pt-br/contato/", "/pt-br/reservar/", "/pt-br/politica-de-privacidade/",
                  "/pt-br/termos-e-condicoes/"],
        "es": ["/es/", "/es/experiencias/", "/es/experiencias/dolphin-bay-boat-tour/", "/es/traslados/",
               "/es/sobre-nosotros/", "/es/contacto/", "/es/reservar/", "/es/politica-de-privacidad/",
               "/es/terminos-y-condiciones/"],
    }

    def test_all_pages_load_in_three_languages(self):
        for lang, urls in self.URLS.items():
            for url in urls:
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, f'<html lang="{lang}"')

    def test_root_redirects_to_default_language(self):
        self.assertRedirects(self.client.get("/"), "/en/", fetch_redirect_response=False)

    def test_pages_are_translated(self):
        self.assertContains(self.client.get("/pt-br/"), "Descubra Pipa.")
        self.assertContains(self.client.get("/es/"), "Descubre Pipa.")
        self.assertContains(self.client.get("/en/"), "Discover Pipa.")
        pt_detail = self.client.get("/pt-br/passeios/dolphin-bay-boat-tour/")
        self.assertContains(pt_detail, "Passeio à Baía dos Golfinhos")
        self.assertContains(pt_detail, "Reservar agora")
        self.assertNotContains(pt_detail, "Book Now")

    def test_seo_tags(self):
        response = self.client.get("/en/experiences/dolphin-bay-boat-tour/")
        self.assertContains(response, 'rel="canonical"')
        self.assertContains(response, 'hreflang="pt-br" href="http://testserver/pt-br/passeios/dolphin-bay-boat-tour/"')
        self.assertContains(response, 'hreflang="es" href="http://testserver/es/experiencias/dolphin-bay-boat-tour/"')
        self.assertContains(response, 'hreflang="x-default"')
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, '"@type": "TouristTrip"')
        self.assertContains(response, '"@type": "BreadcrumbList"')
        self.assertNotContains(response, '"offers"')  # no price filled in -> no invented offer

    def test_structured_data_has_offer_only_with_real_price(self):
        self.boat.price = 250
        self.boat.save()
        response = self.client.get("/en/experiences/dolphin-bay-boat-tour/")
        self.assertContains(response, '"priceCurrency": "BRL"')
        self.assertContains(response, "R$ 250")

    def test_price_on_request_when_empty(self):
        self.assertContains(self.client.get("/en/experiences/"), "Price on request")
        self.assertContains(self.client.get("/pt-br/passeios/"), "Preço sob consulta")

    def test_category_filter(self):
        response = self.client.get("/en/experiences/?category=transfers")
        self.assertContains(response, "Natal Airport to Pipa")
        self.assertNotContains(response, "Dolphin Bay Boat Tour")

    def test_inactive_experience_returns_404(self):
        self.boat.active = False
        self.boat.save()
        self.assertEqual(self.client.get("/en/experiences/dolphin-bay-boat-tour/").status_code, 404)
        self.assertNotContains(self.client.get("/en/experiences/"), "Dolphin Bay Boat Tour")

    def test_transfers_page_shows_route(self):
        response = self.client.get("/pt-br/transfers/")
        self.assertContains(response, "Aeroporto de Natal")
        self.assertContains(response, "Privativo")

    def test_testimonials_hidden_when_none(self):
        self.assertNotContains(self.client.get("/en/"), "What our guests say")

    def test_only_confirmed_testimonials_in_matching_language(self):
        Testimonial.objects.create(author_name="John", text_en="Great day!", confirmed_real=False)
        self.assertNotContains(self.client.get("/en/"), "What our guests say")
        Testimonial.objects.create(author_name="Ana", text_pt="Dia incrível!", confirmed_real=True)
        self.assertNotContains(self.client.get("/en/"), "Dia incrível!")
        self.assertContains(self.client.get("/pt-br/"), "Dia incrível!")

    def test_whatsapp_button_uses_configured_number(self):
        self.assertNotContains(self.client.get("/en/"), "wa.me/")
        site = SiteSettings.load()
        site.whatsapp = "+55 84 98765-4321"
        site.save()
        response = self.client.get("/en/experiences/dolphin-bay-boat-tour/")
        self.assertContains(response, "https://wa.me/5584987654321?text=")
        self.assertContains(response, "Dolphin%20Bay%20Boat%20Tour")

    def test_sitemap_and_robots(self):
        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        content = sitemap.content.decode()
        self.assertIn("/es/experiencias/dolphin-bay-boat-tour/", content)
        self.assertIn('hreflang="pt-br"', content)
        robots = self.client.get("/robots.txt")
        self.assertContains(robots, "Sitemap: http://testserver/sitemap.xml")
        self.assertNotContains(robots, "painel")

    def test_404_page(self):
        response = self.client.get("/es/no-existe/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "marea", status_code=404)


class LanguageSwitchTests(BaseTestCase):
    def test_switch_keeps_page_and_sets_cookie(self):
        response = self.client.get("/i18n/es/", {"next": "/pt-br/passeios/dolphin-bay-boat-tour/"})
        self.assertRedirects(response, "/es/experiencias/dolphin-bay-boat-tour/", fetch_redirect_response=False)
        self.assertEqual(response.cookies["travelpipa_lang"].value, "es")
        # Preference persists: the root now goes to Spanish
        self.assertRedirects(self.client.get("/"), "/es/", fetch_redirect_response=False)

    def test_switch_keeps_query_string(self):
        response = self.client.get("/i18n/pt-br/", {"next": "/en/experiences/?category=transfers"})
        self.assertEqual(response["Location"], "/pt-br/passeios/?category=transfers")

    def test_switch_rejects_external_redirects(self):
        response = self.client.get("/i18n/en/", {"next": "https://evil.example.com/"})
        self.assertEqual(response["Location"], "/en/")

    def test_unknown_language_falls_back_to_default(self):
        response = self.client.get("/i18n/de/", {"next": "/en/"})
        self.assertEqual(response.cookies["travelpipa_lang"].value, "en")


class BookingFlowTests(BaseTestCase):
    def test_preselected_experience(self):
        response = self.client.get("/en/book/?experience=dolphin-bay-boat-tour")
        self.assertEqual(response.context["form"].initial["experience"], self.boat.pk)
        self.assertContains(response, "Quick, with no payment now.")

    def test_valid_request_is_saved_and_not_confirmed(self):
        response = self.client.post(reverse("bookings:request"), self.booking_payload())
        self.assertRedirects(response, reverse("bookings:thanks"))
        booking = BookingRequest.objects.get()
        self.assertEqual(booking.status, BookingRequest.Status.PENDING)
        self.assertEqual(booking.full_name, "Maria Silva")
        self.assertEqual(booking.experience, self.boat)
        self.assertIsNotNone(booking.consent_at)
        thanks = self.client.get(reverse("bookings:thanks"))
        self.assertContains(thanks, booking.reference)
        self.assertContains(thanks, "Your booking is done!")
        # No personal data on the confirmation page
        self.assertNotContains(thanks, "maria@example.com")
        self.assertNotContains(thanks, "7700")

    def test_request_in_portuguese(self):
        url = "/pt-br/reservar/"
        page = self.client.get(url)
        data = self.booking_payload(service_language="pt-br")
        data["form_ts"] = page.context["form"].initial["form_ts"]
        response = self.client.post(url, data)
        self.assertRedirects(response, "/pt-br/reservar/obrigado/")
        self.assertEqual(BookingRequest.objects.get().site_language, "pt-br")
        self.assertContains(self.client.get("/pt-br/reservar/obrigado/"), "Reserva feita!")

    def test_required_fields(self):
        response = self.client.post(reverse("bookings:request"), {"form_ts": self.booking_payload()["form_ts"]})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        for field in ("experience", "preferred_date", "people", "full_name", "email", "phone", "consent"):
            self.assertIn(field, form.errors)
        self.assertEqual(BookingRequest.objects.count(), 0)

    def test_errors_are_translated(self):
        page = self.client.get("/es/reservar/")
        response = self.client.post("/es/reservar/", {"form_ts": page.context["form"].initial["form_ts"]})
        self.assertContains(response, "Acepta los términos de privacidad")

    def test_past_date_rejected(self):
        payload = self.booking_payload(preferred_date=(timezone.localdate() - datetime.timedelta(days=1)).isoformat())
        response = self.client.post(reverse("bookings:request"), payload)
        self.assertIn("preferred_date", response.context["form"].errors)

    def test_invalid_phone_and_people(self):
        response = self.client.post(reverse("bookings:request"), self.booking_payload(phone="123", people=0))
        errors = response.context["form"].errors
        self.assertIn("phone", errors)
        self.assertIn("people", errors)

    def test_inactive_experience_cannot_be_booked(self):
        payload = self.booking_payload()
        self.boat.active = False
        self.boat.save()
        response = self.client.post(reverse("bookings:request"), payload)
        self.assertIn("experience", response.context["form"].errors)

    def test_honeypot_blocks_bots(self):
        response = self.client.post(reverse("bookings:request"), self.booking_payload(website="http://spam"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BookingRequest.objects.count(), 0)

    @override_settings(FORM_MIN_FILL_SECONDS=30)
    def test_too_fast_submission_blocked(self):
        response = self.client.post(reverse("bookings:request"), self.booking_payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BookingRequest.objects.count(), 0)

    def test_tampered_timestamp_blocked(self):
        self.client.post(reverse("bookings:request"), self.booking_payload(form_ts="forged"))
        self.assertEqual(BookingRequest.objects.count(), 0)

    @override_settings(FORM_RATE_LIMIT_PER_HOUR=2)
    def test_rate_limit(self):
        for _ in range(3):
            self.client.post(reverse("bookings:request"), self.booking_payload())
        self.assertEqual(BookingRequest.objects.count(), 2)

    def test_csrf_is_enforced(self):
        from django.test import Client

        strict = Client(enforce_csrf_checks=True)
        response = strict.post(reverse("bookings:request"), {"full_name": "x"})
        self.assertEqual(response.status_code, 403)

    def test_thanks_page_requires_a_request(self):
        self.assertRedirects(self.client.get(reverse("bookings:thanks")), reverse("bookings:request"))

    def test_no_email_without_smtp(self):
        self.client.post(reverse("bookings:request"), self.booking_payload())
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(BookingRequest.objects.get().notification_sent)

    @override_settings(EMAIL_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                       NOTIFICATION_EMAILS=["team@example.com"])
    def test_admin_notified_when_smtp_configured(self):
        self.client.post(reverse("bookings:request"), self.booking_payload())
        booking = BookingRequest.objects.get()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(booking.reference, mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["team@example.com"])
        self.assertIn("aguarda o contato da equipe", mail.outbox[0].body)
        self.assertTrue(booking.notification_sent)


class ContactFormTests(BaseTestCase):
    def test_contact_message_saved(self):
        from core.models import ContactMessage

        page = self.client.get("/en/contact/")
        data = {"name": "Tom", "email": "tom@example.com", "message": "Hello!", "consent": "on",
                "form_ts": page.context["form"].initial["form_ts"]}
        response = self.client.post("/en/contact/", data, follow=True)
        self.assertContains(response, "Your message was sent")
        self.assertEqual(ContactMessage.objects.get().language, "en")

    def test_contact_requires_consent(self):
        page = self.client.get("/en/contact/")
        data = {"name": "Tom", "email": "tom@example.com", "message": "Hello!",
                "form_ts": page.context["form"].initial["form_ts"]}
        response = self.client.post("/en/contact/", data)
        self.assertIn("consent", response.context["form"].errors)


class AdminTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_user = get_user_model().objects.create_superuser("admin", "admin@example.com", "S3cure-pass-123")

    def test_admin_requires_login(self):
        response = self.client.get("/painel/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/painel/login/", response["Location"])
        self.assertEqual(self.client.get("/admin/").status_code, 404)

    def test_admin_pages_load_in_portuguese(self):
        self.client.force_login(self.admin_user)
        BookingRequest.objects.create(experience=self.boat, preferred_date=timezone.localdate(), people=2,
                                      full_name="Maria", email="m@example.com", phone="+5584999999999")
        for url in ["/painel/", "/painel/tours/experience/", "/painel/tours/experience/add/",
                    f"/painel/tours/experience/{self.boat.pk}/change/", "/painel/tours/category/",
                    "/painel/bookings/bookingrequest/", "/painel/bookings/bookingrequest/?status__exact=pending",
                    f"/painel/bookings/bookingrequest/{BookingRequest.objects.get().pk}/change/",
                    "/painel/core/testimonial/", "/painel/core/contactmessage/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
        self.assertContains(self.client.get("/painel/"), "Solicitações de reserva")

    def test_settings_changelist_goes_to_single_form(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/painel/core/sitesettings/")
        self.assertRedirects(response, "/painel/core/sitesettings/1/change/")

    def _experience_form_data(self, **overrides):
        data = {
            "category": self.boats.pk, "slug": "", "title_en": "Sunset Lagoon Cruise",
            "title_pt": "Pôr do sol na lagoa", "title_es": "Atardecer en la laguna",
            "order": 0, "currency": "BRL", "price_unit": "person", "price_is_starting": "on", "active": "on",
            "price": "180",
            "images-TOTAL_FORMS": "1", "images-INITIAL_FORMS": "0", "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "1000",
            "images-0-image": make_image(), "images-0-is_cover": "on", "images-0-order": "0",
            "images-0-alt_en": "Boat at sunset",
        }
        data.update(overrides)
        return data

    def test_create_and_edit_experience_through_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.post("/painel/tours/experience/add/", self._experience_form_data())
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and
                         response.context["adminform"].form.errors)
        exp = Experience.objects.get(title_en="Sunset Lagoon Cruise")
        self.assertEqual(exp.slug, "sunset-lagoon-cruise")
        self.assertEqual(exp.images.count(), 1)

        # Edit: change the price and deactivate
        data = self._experience_form_data(price="200", active="", **{
            "images-TOTAL_FORMS": "1", "images-INITIAL_FORMS": "1",
            "images-0-id": exp.images.get().pk, "images-0-experience": exp.pk, "slug": exp.slug,
        })
        data.pop("images-0-image")
        response = self.client.post(f"/painel/tours/experience/{exp.pk}/change/", data)
        self.assertEqual(response.status_code, 302)
        exp.refresh_from_db()
        self.assertEqual(exp.price, 200)
        self.assertFalse(exp.active)
        self.assertEqual(self.client.get("/en/experiences/sunset-lagoon-cruise/").status_code, 404)

    def test_transfer_requires_route(self):
        self.client.force_login(self.admin_user)
        data = self._experience_form_data(category=self.transfers_cat.pk, title_en="Shared shuttle")
        response = self.client.post("/painel/tours/experience/add/", data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Experience.objects.filter(title_en="Shared shuttle").exists())

    def test_change_booking_status_and_notes(self):
        self.client.force_login(self.admin_user)
        booking = BookingRequest.objects.create(experience=self.boat, preferred_date=timezone.localdate(),
                                                people=2, full_name="Maria", email="m@example.com",
                                                phone="+5584999999999")
        response = self.client.post(f"/painel/bookings/bookingrequest/{booking.pk}/change/", {
            "experience": self.boat.pk, "status": "contacted", "internal_notes": "Called on WhatsApp",
        })
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "contacted")
        self.assertEqual(booking.internal_notes, "Called on WhatsApp")
        self.assertEqual(booking.full_name, "Maria")  # customer data is read-only

    def test_bulk_status_action(self):
        self.client.force_login(self.admin_user)
        booking = BookingRequest.objects.create(experience=self.boat, preferred_date=timezone.localdate(),
                                                people=2, full_name="Maria", email="m@example.com",
                                                phone="+5584999999999")
        self.client.post("/painel/bookings/bookingrequest/", {"action": "mark_confirmed",
                                                              "_selected_action": [booking.pk]})
        booking.refresh_from_db()
        self.assertEqual(booking.status, "confirmed")


class DemoSeedTests(TestCase):
    @override_settings(MEDIA_ROOT=TEMP_MEDIA, SITE_URL="")
    def test_seed_demo_creates_marked_content_without_prices(self):
        from django.core.management import call_command

        call_command("seed_demo", verbosity=0, stdout=StringIO())
        self.assertEqual(Category.objects.count(), 5)
        demo = Experience.objects.filter(is_demo=True)
        self.assertEqual(demo.count(), 4)
        self.assertFalse(demo.exclude(price=None).exists())
        self.assertEqual(Testimonial.objects.count(), 0)
        self.assertContains(self.client.get("/en/experiences/dolphin-bay-boat-tour/"), "Demo content.")
        self.assertContains(self.client.get("/en/experiences/dolphin-bay-boat-tour/"), 'content="noindex, follow"')
        call_command("seed_demo", verbosity=0, stdout=StringIO())  # idempotent
        self.assertEqual(Experience.objects.filter(is_demo=True).count(), 4)


class LoadToursTests(TestCase):
    @override_settings(SITE_URL="", MEDIA_ROOT=TEMP_MEDIA)
    def test_load_tours_creates_real_experiences_in_three_languages(self):
        from django.core.management import call_command

        call_command("load_tours", stdout=StringIO())
        call_command("load_tours", stdout=StringIO())  # idempotent
        boat = Experience.objects.get(slug="pipa-dolphin-bay-speedboat-tour")
        self.assertFalse(boat.is_demo)
        self.assertEqual(boat.price, 70)
        self.assertEqual(Experience.objects.filter(is_demo=False).count(), 7)
        self.assertContains(self.client.get("/pt-br/passeios/guarairas-lagoon-gastronomic-boat-tour/"), "R$ 325")
        self.assertContains(self.client.get("/pt-br/passeios/pipa-dolphin-bay-speedboat-tour/"), "A partir de")
        self.assertContains(self.client.get("/en/experiences/pipa-dolphin-bay-speedboat-tour/"), "Dolphin Bay")
        jeep = self.client.get("/es/experiencias/southern-coast-4x4-jeep-tour/")
        self.assertContains(jeep, "Laguna de Guaraíras")
        self.assertContains(jeep, "R$ 120")

        # Photos and video from content/ are attached once, never duplicated
        self.assertEqual(boat.images.count(), 4)
        self.assertTrue(boat.images.filter(is_cover=True).exists())
        self.assertTrue(boat.video)
        detail = self.client.get("/pt-br/passeios/pipa-dolphin-bay-speedboat-tour/")
        self.assertContains(detail, "<video")
        self.assertContains(detail, "Veja como é o passeio")
        self.assertContains(self.client.get("/en/experiences/"), "bi-play-circle-fill")
        # Files are the originals, without re-encoding
        from tours.management.commands.load_tours import CONTENT_DIR
        with boat.video.open("rb") as fh:
            self.assertEqual(fh.read(), (CONTENT_DIR / "videos/lancha-baia-dos-golfinhos.mp4").read_bytes())
        cover = boat.images.get(is_cover=True)
        with cover.image.open("rb") as fh:
            self.assertEqual(fh.read(), (CONTENT_DIR / "photos/lancha/01-lancha-com-turistas.jpg").read_bytes())
        # Transfer: 9 real photos; a new run adds nothing and keeps the cover
        transfer = Experience.objects.get(slug="natal-airport-pipa-transfer")
        self.assertEqual(transfer.images.count(), 9)
        self.assertEqual(transfer.images.filter(is_cover=True).count(), 1)
        self.assertContains(self.client.get("/pt-br/passeios/natal-airport-pipa-transfer/"), "7 lugares")
        # Trust badges: strip on every page, DER on the transfer, Cadastur on guided tours
        pt_transfer = self.client.get("/pt-br/passeios/natal-airport-pipa-transfer/")
        self.assertContains(pt_transfer, "Veículos cadastrados para transporte turístico no DER/RN.")
        self.assertContains(pt_transfer, "Guias de turismo com Cadastur")  # strip
        self.assertNotContains(pt_transfer, "Guia de turismo com cadastro no Cadastur")  # no guide on transfers
        self.assertContains(self.client.get("/es/experiencias/quad-bike-tour-route-1/"),
                            "Guía de turismo registrado en Cadastur")
        self.assertNotContains(self.client.get("/en/experiences/pipa-dolphin-bay-speedboat-tour/"),
                               "Tour guide registered in Cadastur")
        site = SiteSettings.load()
        site.trust_cadastur_guides = False
        site.save()
        self.assertNotContains(self.client.get("/en/"), "Licensed tour guides")
        self.assertContains(self.client.get("/en/"), "Registered tourist vehicles")
        site.trust_cadastur_guides = True
        site.save()
        # Home page banner set from content/ (original file, no re-encoding)
        site = SiteSettings.load()
        self.assertTrue(site.hero_image)
        with site.hero_image.open("rb") as fh:
            self.assertEqual(fh.read(), (CONTENT_DIR / "photos/site/pipa-panorama-por-do-sol.jpg").read_bytes())
        self.assertContains(self.client.get("/en/"), site.hero_image.url)
        self.assertNotContains(self.client.get("/en/"), "Demo image — replace in the admin panel")
        # --replace-media swaps the files without duplicating them
        call_command("load_tours", "--replace-media", stdout=StringIO())
        boat.refresh_from_db()
        self.assertEqual(boat.images.count(), 4)
        self.assertTrue(boat.video)


@override_settings(MEDIA_ROOT=TEMP_MEDIA, SERVE_MEDIA=True)
class MediaServingTests(TestCase):
    def setUp(self):
        import os

        os.makedirs(os.path.join(TEMP_MEDIA, "test"), exist_ok=True)
        self.path = os.path.join(TEMP_MEDIA, "test", "clip.mp4")
        with open(self.path, "wb") as fh:
            fh.write(bytes(range(256)) * 4)  # 1024 bytes

    def test_full_file(self):
        response = self.client.get("/media/test/clip.mp4")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(response["Content-Type"], "video/mp4")
        self.assertEqual(len(b"".join(response.streaming_content)), 1024)

    def test_range_request_for_safari(self):
        response = self.client.get("/media/test/clip.mp4", headers={"Range": "bytes=0-1"})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], "bytes 0-1/1024")
        self.assertEqual(b"".join(response.streaming_content), bytes([0, 1]))
        tail = self.client.get("/media/test/clip.mp4", headers={"Range": "bytes=-4"})
        self.assertEqual(tail["Content-Range"], "bytes 1020-1023/1024")
        open_end = self.client.get("/media/test/clip.mp4", headers={"Range": "bytes=1000-"})
        self.assertEqual(open_end["Content-Length"], "24")

    def test_invalid_range(self):
        response = self.client.get("/media/test/clip.mp4", headers={"Range": "bytes=5000-6000"})
        self.assertEqual(response.status_code, 416)

    def test_path_traversal_blocked(self):
        self.assertEqual(self.client.get("/media/../config/settings.py").status_code, 404)
        self.assertEqual(self.client.get("/media/%2e%2e/config/settings.py").status_code, 404)
        self.assertEqual(self.client.get("/media/missing.jpg").status_code, 404)

    def test_post_not_allowed(self):
        self.assertEqual(self.client.post("/media/test/clip.mp4").status_code, 405)
