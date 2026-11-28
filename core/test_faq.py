import json
import re

from django.test import TestCase

from core.faq import faq_items


class FaqPageTests(TestCase):
    def schema(self, response):
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', response.content.decode(), re.S)
        return [json.loads(b) for b in blocks]

    def test_english_page_and_schema(self):
        response = self.client.get("/en/faq/")
        self.assertContains(response, "What if my flight is delayed?")
        self.assertContains(response, "48 hours")
        faq = next(s for s in self.schema(response) if s.get("@type") == "FAQPage")
        self.assertEqual(len(faq["mainEntity"]), len(faq_items()))

    def test_portuguese_and_spanish(self):
        pt = self.client.get("/pt-br/duvidas-frequentes/")
        self.assertContains(pt, "E se meu voo atrasar?")
        self.assertContains(pt, "Os 90% restantes são pagos no dia")
        faq = next(s for s in self.schema(pt) if s.get("@type") == "FAQPage")
        self.assertEqual(faq["mainEntity"][0]["name"], "A TravelPipa é mesmo uma agência local?")
        es = self.client.get("/es/preguntas-frecuentes/")
        self.assertContains(es, "¿Y si mi vuelo se retrasa?")

    def test_linked_from_footer_and_sitemap(self):
        self.assertContains(self.client.get("/en/"), 'href="/en/faq/"')
        self.assertContains(self.client.get("/sitemap.xml"), "/faq/")
