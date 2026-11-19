"""Google Ads tag: only on the public site, only when enabled, and allowed by the CSP."""
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from core.middleware import CONTENT_SECURITY_POLICY


@override_settings(GOOGLE_ADS_ENABLED=True, GOOGLE_ADS_ID="AW-123", GOOGLE_ADS_WHATSAPP_LABEL="abcLabel")
class GoogleAdsEnabledTests(TestCase):
    def test_tag_and_whatsapp_conversion_on_public_pages(self):
        html = self.client.get("/pt-br/").content.decode()
        self.assertIn("https://www.googletagmanager.com/gtag/js?id=AW-123", html)
        self.assertIn('data-id="AW-123"', html)
        self.assertIn('data-whatsapp="AW-123/abcLabel"', html)
        self.assertIn("js/google-ads.js", html)

    def test_csp_allows_the_google_tag_on_public_pages(self):
        csp = self.client.get("/en/")["Content-Security-Policy"]
        self.assertIn("script-src 'self' https://www.googletagmanager.com", csp)
        self.assertIn("https://googleads.g.doubleclick.net", csp)
        self.assertIn("frame-ancestors 'none'", csp)

    def test_panel_keeps_the_strict_policy_and_no_tag(self):
        for path in (reverse("panel:login"), "/" + settings.PANEL_URL + "does-not-exist/"):
            response = self.client.get(path)
            self.assertEqual(response["Content-Security-Policy"], CONTENT_SECURITY_POLICY, path)
            self.assertNotIn("googletagmanager", response.content.decode(), path)

    @override_settings(GOOGLE_ADS_WHATSAPP_LABEL="")
    def test_tag_without_conversion_label(self):
        html = self.client.get("/en/").content.decode()
        self.assertIn('data-whatsapp=""', html)


@override_settings(GOOGLE_ADS_ENABLED=False)
class GoogleAdsDisabledTests(TestCase):
    def test_no_tag_and_strict_csp(self):
        response = self.client.get("/en/")
        self.assertNotIn("googletagmanager", response.content.decode())
        self.assertEqual(response["Content-Security-Policy"], CONTENT_SECURITY_POLICY)
        self.assertNotIn("googletagmanager", CONTENT_SECURITY_POLICY)
