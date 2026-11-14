"""Launch hardening: real client IP, canonical host, headers, media whitelist, login limits, e-mail."""
import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from bookings.notifications import one_line
from core.antispam import client_ip
from core.email_backends import ResendEmailBackend


class ClientIpTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_forged_left_entries_are_ignored(self):
        request = self.rf.get("/", HTTP_X_FORWARDED_FOR="1.1.1.1, 198.51.100.7", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(client_ip(request), "198.51.100.7")

    @override_settings(TRUSTED_PROXY_COUNT=2)
    def test_two_proxies(self):
        request = self.rf.get("/", HTTP_X_FORWARDED_FOR="1.1.1.1, 198.51.100.7, 172.70.1.1")
        self.assertEqual(client_ip(request), "198.51.100.7")

    def test_without_proxy_header(self):
        self.assertEqual(client_ip(self.rf.get("/", REMOTE_ADDR="192.0.2.5")), "192.0.2.5")


@override_settings(DEBUG=False, CANONICAL_HOST="travelpipa.com.br",
                   ALLOWED_HOSTS=["travelpipa.com.br", "www.travelpipa.com.br", "x.up.railway.app"])
class CanonicalHostTests(TestCase):
    def test_www_redirects_to_main_domain(self):
        response = self.client.get("/en/?a=1", HTTP_HOST="www.travelpipa.com.br")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://travelpipa.com.br/en/?a=1")

    def test_railway_address_redirects(self):
        response = self.client.get("/pt-br/", HTTP_HOST="x.up.railway.app")
        self.assertEqual(response["Location"], "https://travelpipa.com.br/pt-br/")

    def test_health_check_on_any_host(self):
        self.assertEqual(self.client.get("/healthz/", HTTP_HOST="x.up.railway.app").status_code, 200)

    def test_main_domain_is_served(self):
        self.assertEqual(self.client.get("/en/", HTTP_HOST="travelpipa.com.br").status_code, 200)


class HeaderAndMediaTests(TestCase):
    def test_security_headers_on_pages(self):
        response = self.client.get("/en/")
        self.assertIn("script-src 'self'", response["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertIn("camera=()", response["Permissions-Policy"])

    @override_settings(SERVE_MEDIA=True)
    def test_only_photos_and_videos_are_served(self):
        from core.media_views import serve_media
        rf = RequestFactory()
        for name in ("page.html", "image.svg", "script.js", "../config/settings.py"):
            with self.assertRaises(Exception):
                serve_media(rf.get("/media/" + name), name)


class LoginLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        get_user_model().objects.create_user("equipe", "e@example.com", "Senha-forte-123", is_staff=True)

    def test_rotating_ips_does_not_bypass_the_lock(self):
        url = reverse("panel:login")
        with self.settings(PANEL_LOGIN_MAX_ATTEMPTS=2):
            for n in range(8):  # 2 * 4 attempts from different addresses
                self.client.post(url, {"username": "equipe", "password": "errada"},
                                 HTTP_X_FORWARDED_FOR=f"198.51.100.{n}")
            response = self.client.post(url, {"username": "equipe", "password": "Senha-forte-123"},
                                        HTTP_X_FORWARDED_FOR="203.0.113.50")
        self.assertEqual(response.status_code, 200)  # still on the login page: locked
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_login_goes_through_the_panel_login(self):
        response = self.client.get("/painel/login/?next=/painel/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("panel:login")))
        self.assertIn("next=", response["Location"])


class EmailTests(TestCase):
    def test_subject_cannot_carry_line_breaks(self):
        self.assertEqual(one_line("Oi\r\nBcc: x@evil.com"), "Oi Bcc: x@evil.com")

    @override_settings(RESEND_API_KEY="re_test")
    def test_resend_backend_posts_json(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return b'{"id":"1"}'

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["auth"] = request.headers["Authorization"]
            captured["data"] = json.loads(request.data)
            return FakeResponse()

        message = EmailMessage("Assunto", "Corpo", "TravelPipa <suporte@travelpipa.com.br>",
                               ["equipe@travelpipa.com.br"], reply_to=["cliente@example.com"])
        with mock.patch("urllib.request.urlopen", fake_urlopen):
            self.assertEqual(ResendEmailBackend().send_messages([message]), 1)
        self.assertEqual(captured["url"], "https://api.resend.com/emails")
        self.assertEqual(captured["auth"], "Bearer re_test")
        self.assertEqual(captured["data"]["reply_to"], ["cliente@example.com"])
        self.assertEqual(captured["data"]["to"], ["equipe@travelpipa.com.br"])

    @override_settings(EMAIL_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                       NOTIFICATION_EMAILS=["equipe@example.com"])
    def test_notification_links_to_panel_and_replies_to_customer(self):
        from bookings.models import BookingRequest
        from bookings.notifications import notify_new_booking
        from tours.models import Category, Experience
        import datetime
        cat = Category.objects.create(name_en="Boat", slug="boat")
        exp = Experience.objects.create(category=cat, title_en="Boat tour", slug="boat-tour")
        booking = BookingRequest.objects.create(
            experience=exp, experience_title="Boat tour", preferred_date=datetime.date(2027, 1, 10), people=2,
            full_name="Ana", email="ana@example.com", phone="+55 84 99999-0000")
        self.assertTrue(notify_new_booking(RequestFactory().get("/"), booking))
        self.assertEqual(mail.outbox[0].reply_to, ["ana@example.com"])
        self.assertIn(reverse("panel:booking_detail", args=[booking.pk]), mail.outbox[0].body)


class PrepareSitePasswordTests(TestCase):
    def test_variable_resets_existing_user_password(self):
        from django.core.management import call_command
        import io
        User = get_user_model()
        User.objects.create_superuser("equipe", "e@example.com", "Senha-antiga-123")
        cache.set("panel-login-user:x", 99)
        env = {"DJANGO_SUPERUSER_USERNAME": "Equipe", "DJANGO_SUPERUSER_PASSWORD": "Senha-nova-456"}
        with mock.patch.dict("os.environ", env), mock.patch("core.management.commands.prepare_site.call_command"):
            call_command("prepare_site", stdout=io.StringIO())
        self.assertTrue(User.objects.get(username="equipe").check_password("Senha-nova-456"))
        self.assertIsNone(cache.get("panel-login-user:x"))


class PrepareSiteNewToursTests(TestCase):
    def test_only_missing_tours_are_created_and_edits_are_kept(self):
        from django.core.management import call_command
        import io
        from tours.models import Experience
        call_command("load_tours", stdout=io.StringIO())
        airport = Experience.objects.get(slug="natal-airport-pipa-transfer")
        airport.title_pt = "Editado no painel"
        airport.save()
        Experience.objects.filter(slug="pipa-ponta-negra-natal-transfer").delete()
        call_command("prepare_site", stdout=io.StringIO())
        self.assertTrue(Experience.objects.filter(slug="pipa-ponta-negra-natal-transfer").exists())
        self.assertEqual(Experience.objects.get(slug="natal-airport-pipa-transfer").title_pt, "Editado no painel")


class ContentFitsDatabaseTests(TestCase):
    """Postgres rejects text longer than the column (SQLite does not): check every built-in text."""

    def test_all_tour_texts_fit_their_columns(self):
        from tours.management.commands.load_tours import TOURS
        from tours.models import Experience, ExperienceImage
        problems = []
        for tour in TOURS:
            for lang in ("pt", "en", "es"):
                for key, value in tour[lang].items():
                    limit = Experience._meta.get_field(f"{key}_{lang}").max_length
                    if limit and len(value) > limit:
                        problems.append(f"{tour['slug']} {key}_{lang}: {len(value)} > {limit}")
            for photo in tour.get("media", {}).get("photos", []):
                for index, lang in enumerate(("pt", "en", "es"), start=1):
                    limit = ExperienceImage._meta.get_field(f"alt_{lang}").max_length
                    if limit and len(photo[index]) > limit:
                        problems.append(f"{tour['slug']} alt_{lang}: {len(photo[index])} > {limit}")
        self.assertEqual(problems, [])

    def test_wording_update_never_exceeds_columns(self):
        from tours.discount_wording import REPLACEMENTS
        from tours.models import Experience
        limit = Experience._meta.get_field("meta_description_pt").max_length
        old = ("Transfer com motorista entre o Aeroporto de Natal e Pipa a partir de R$ 240 por carro "
               "(até 3 pessoas). Desconto na ida e volta e carros de 7 lugares para grupos.")
        from tours.discount_wording import apply
        self.assertLessEqual(len(apply(old)), limit)
        self.assertTrue(REPLACEMENTS)


class MediaRepairTests(TestCase):
    def test_missing_photo_is_restored_from_content(self):
        import io
        import shutil
        import tempfile
        from django.core.management import call_command
        from tours.models import ExperienceImage
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with self.settings(MEDIA_ROOT=media):
            call_command("load_tours", stdout=io.StringIO())
            image = ExperienceImage.objects.filter(experience__slug="southern-coast-4x4-jeep-tour").first()
            image.image.storage.delete(image.image.name)
            self.assertFalse(image.image.storage.exists(image.image.name))
            call_command("prepare_site", stdout=io.StringIO())
            self.assertTrue(image.image.storage.exists(image.image.name))
