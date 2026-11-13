"""Tests for the tides & weather feature (external APIs are simulated)."""
import datetime as dt
import json
from pathlib import Path
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import translation

from core import conditions
from tours.models import Category, Experience

DATA = Path(__file__).parent / "test_data"
METNO = json.loads((DATA / "metno_compact.json").read_text())
WORLDTIDES = json.loads((DATA / "worldtides_extremes.json").read_text())
TABUAMARE = json.loads((DATA / "tabuamare_geo.json").read_text())
# 13:00 in Pipa on the day of the sample data (first low tide at 04:12, next at 16:36)
FIXED_NOW = dt.datetime(2026, 11, 11, 13, 0, tzinfo=conditions.LOCAL_TZ)


def fake_api(url, params=None, headers=None):
    if url == conditions.METNO_URL:
        return METNO
    if url == conditions.WORLDTIDES_URL:
        return WORLDTIDES
    if url.startswith(conditions.TABUAMARE_URL + "/geo-tabua-mare/"):
        return TABUAMARE
    raise AssertionError(url)


@override_settings(SITE_URL="", WORLDTIDES_API_KEY="", TABUAMARE_API_KEY="", TIDES_PROVIDER="tabuamare",
                   TIDES_STATE="rn", WEATHER_ENABLED=True)
class ConditionsServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        patcher = mock.patch.object(conditions, "now", return_value=FIXED_NOW)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_parse_metno(self):
        data = conditions.parse_metno(METNO, today=FIXED_NOW.date())
        self.assertEqual(data["current"]["temperature"], 29)
        self.assertEqual(data["current"]["wind_kmh"], 19)  # 5.4 m/s
        self.assertEqual(len(data["daily"]), 6)
        self.assertEqual(data["daily"][0]["date"], "2026-11-11")
        self.assertGreaterEqual(data["daily"][0]["max"], data["daily"][0]["min"])
        # Rain is counted once even where 1h and 6h blocks overlap
        self.assertEqual(data["daily"][2]["rain_mm"], 0.4)

    def test_symbols(self):
        self.assertEqual(conditions.symbol_info("clearsky_night")["icon"], "moon-stars")
        self.assertEqual(conditions.symbol_info("heavyrainandthunder")["icon"], "cloud-lightning-rain")
        self.assertEqual(conditions.symbol_info("unknown_code")["icon"], "cloud-sun")
        with translation.override("pt-br"):
            self.assertEqual(conditions.symbol_info("partlycloudy_day")["label"], "Parcialmente nublado")

    def test_sun_times_for_pipa(self):
        sun = conditions.sun_times(dt.date(2026, 11, 11))
        self.assertEqual(sun["sunrise"].strftime("%H"), "04")
        self.assertTrue(dt.time(17, 0) <= sun["sunset"].time() <= dt.time(17, 40))

    def test_weather_is_cached_and_identifies_the_site(self):
        with mock.patch.object(conditions, "_get_json", side_effect=fake_api) as api:
            first = conditions.get_weather()
            second = conditions.get_weather()
        self.assertEqual(api.call_count, 1)
        self.assertEqual(first["current"]["temperature"], second["current"]["temperature"])
        self.assertIn("TravelPipa", api.call_args.kwargs["headers"]["User-Agent"])
        self.assertEqual(api.call_args.args[1], {"lat": -6.2283, "lon": -35.0464})

    def test_provider_down_uses_last_good_data_and_backs_off(self):
        with mock.patch.object(conditions, "_get_json", side_effect=fake_api):
            good = conditions.get_weather()
        cache.delete("conditions:weather")  # fresh copy expired, stale copy remains
        with mock.patch.object(conditions, "_get_json", side_effect=OSError("timeout")) as api:
            self.assertEqual(conditions.get_weather()["current"], good["current"])
            conditions.get_weather()
        self.assertEqual(api.call_count, 1)  # no retry storm while the provider is down

    def test_provider_down_without_previous_data(self):
        with mock.patch.object(conditions, "_get_json", side_effect=OSError("down")):
            self.assertIsNone(conditions.get_weather())

    @override_settings(TIDES_PROVIDER="worldtides")
    def test_worldtides_disabled_without_key(self):
        with mock.patch.object(conditions, "_get_json") as api:
            self.assertIsNone(conditions.get_tides())
        api.assert_not_called()

    def test_tabuamare_is_free_and_enabled_by_default(self):
        self.assertTrue(conditions.tides_enabled())
        with mock.patch.object(conditions, "_get_json", side_effect=fake_api) as api:
            tides = conditions.get_tides()
        url = api.call_args.args[0]
        self.assertEqual(url, conditions.TABUAMARE_URL + "/geo-tabua-mare/[-6.2283,-35.0464]/rn/11/[11-18]")
        self.assertNotIn("Authorization", api.call_args.kwargs["headers"])
        first = tides["days"][0]["events"][0]
        self.assertEqual((first["type"], first["time"].strftime("%H:%M"), first["height"]), ("low", "04:12", 0.2))
        self.assertEqual(tides["days"][0]["events"][1]["type"], "high")
        self.assertEqual(tides["next_low"]["time"].strftime("%H:%M"), "16:36")
        self.assertIn("PORTO DE NATAL", tides["copyright"])
        self.assertIn("DHN", tides["copyright"])

    @override_settings(TABUAMARE_API_KEY="free-key")
    def test_tabuamare_key_is_sent_when_configured(self):
        with mock.patch.object(conditions, "_get_json", side_effect=fake_api) as api:
            conditions.get_tides()
        self.assertEqual(api.call_args.kwargs["headers"]["Authorization"], "Bearer free-key")

    def test_tabuamare_requests_split_across_months_and_stop_at_year_end(self):
        calls = []

        def capture(url, params=None, headers=None):
            calls.append(url.split("/geo-tabua-mare/")[1])
            return TABUAMARE

        with mock.patch.object(conditions, "_get_json", side_effect=capture):
            with mock.patch.object(conditions, "now", return_value=FIXED_NOW.replace(day=27)):
                conditions._load_tabuamare()
            with mock.patch.object(conditions, "now", return_value=FIXED_NOW.replace(month=12, day=28)):
                conditions._load_tabuamare()
        self.assertEqual(calls[:2], ["[-6.2283,-35.0464]/rn/11/[27-30]", "[-6.2283,-35.0464]/rn/12/[1-4]"])
        self.assertEqual(calls[2:], ["[-6.2283,-35.0464]/rn/12/[28-31]"])

    def test_tabuamare_error_response(self):
        self.assertIsNone(conditions.parse_tabuamare({"error": "Too many requests"}))
        self.assertIsNone(conditions.parse_tabuamare({"data": [], "total": 0}))

    def test_days_param(self):
        self.assertEqual(conditions._days_param([3, 1, 4, 5]), "[1,3-5]")

    @override_settings(WORLDTIDES_API_KEY="test-key", TIDES_PROVIDER="worldtides")
    def test_tides_grouped_by_local_day(self):
        with mock.patch.object(conditions, "_get_json", side_effect=fake_api) as api:
            tides = conditions.get_tides()
        params = api.call_args.args[1]
        self.assertEqual(params["date"], "2026-11-11")
        self.assertEqual(params["datum"], "CD")
        self.assertEqual(tides["days"][0]["date"], dt.date(2026, 11, 11))
        first = tides["days"][0]["events"][0]
        self.assertEqual((first["type"], first["time"].strftime("%H:%M"), first["past"]), ("low", "04:12", True))
        self.assertEqual(tides["next_low"]["time"].strftime("%H:%M"), "16:36")
        self.assertTrue(all(not e["past"] for e in tides["upcoming_lows"]))
        self.assertLessEqual(len(tides["days"]), 7)

    def test_worldtides_error_response(self):
        self.assertIsNone(conditions.parse_worldtides({"status": 400, "error": "INVALID_KEY"}))


@override_settings(SITE_URL="", WORLDTIDES_API_KEY="", TABUAMARE_API_KEY="", TIDES_PROVIDER="tabuamare",
                   TIDES_STATE="rn", WEATHER_ENABLED=True)
class ConditionsPagesTests(TestCase):
    def setUp(self):
        cache.clear()
        for target, value in ((conditions, "now"),):
            patcher = mock.patch.object(target, value, return_value=FIXED_NOW)
            patcher.start()
            self.addCleanup(patcher.stop)
        api = mock.patch.object(conditions, "_get_json", side_effect=fake_api)
        api.start()
        self.addCleanup(api.stop)
        cat = Category.objects.create(name_en="Adventure", slug="adventure-tours")
        self.tide_tour = Experience.objects.create(category=cat, title_en="Jeep Tour", tide_dependent=True)
        self.other = Experience.objects.create(category=cat, title_en="Boat Tour")

    def test_page_in_three_languages(self):
        for url, text in (("/en/tides-and-weather/", "Tides and weather in Pipa"),
                          ("/pt-br/mare-e-tempo/", "Maré e tempo em Pipa"),
                          ("/es/mareas-y-clima/", "Mareas y clima en Pipa")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, text)
                self.assertContains(response, "MET Norway")
                self.assertContains(response, "29°C")

    def test_free_tide_table_shown_by_default(self):
        response = self.client.get("/pt-br/mare-e-tempo/")
        self.assertContains(response, "Maré baixa")
        self.assertContains(response, "16:36")
        self.assertContains(response, "PORTO DE NATAL (RN) (DHN)")
        self.assertContains(response, "Tábua de Maré API")

    @override_settings(TIDES_PROVIDER="worldtides")
    def test_without_tide_key_links_to_navy_tables(self):
        response = self.client.get("/pt-br/mare-e-tempo/")
        self.assertContains(response, conditions.NAVY_TIDE_TABLES_URL)
        self.assertNotContains(response, "tide-list")
        self.assertContains(response, "Jeep Tour")  # tours that depend on the tide

    @override_settings(WORLDTIDES_API_KEY="test-key", TIDES_PROVIDER="worldtides")
    def test_with_tide_key_shows_table_and_attribution(self):
        response = self.client.get("/pt-br/mare-e-tempo/")
        self.assertContains(response, "Maré baixa")
        self.assertContains(response, "16:36")
        self.assertContains(response, "worldtides.info")

    def test_widgets(self):
        compact = self.client.get("/pt-br/widgets/conditions/")
        self.assertEqual(compact.status_code, 200)
        self.assertEqual(compact["X-Robots-Tag"], "noindex")
        self.assertContains(compact, "29°C")
        self.assertContains(compact, "Próxima maré baixa")
        tide = self.client.get("/es/widgets/conditions/?v=tide")
        self.assertContains(tide, "Mejor con marea baja")
        self.assertContains(tide, "16:36")

    def test_tide_box_only_on_tide_dependent_tours(self):
        self.assertContains(self.client.get(self.tide_tour.get_absolute_url()), "v=tide")
        self.assertNotContains(self.client.get(self.other.get_absolute_url()), "v=tide")

    def test_home_loads_without_calling_apis(self):
        with mock.patch.object(conditions, "_get_json") as api:
            response = self.client.get("/en/")
        api.assert_not_called()  # widgets are loaded asynchronously
        self.assertContains(response, "data-fragment")

    def test_pages_still_work_when_providers_fail(self):
        with mock.patch.object(conditions, "_get_json", side_effect=OSError("down")):
            response = self.client.get("/en/tides-and-weather/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "temporarily unavailable")

    def test_sitemap_lists_page(self):
        content = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/pt-br/mare-e-tempo/", content)
