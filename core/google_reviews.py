"""
Google reviews of the TravelPipa Business Profile.

* ``write_review_url`` — the official "write a review" link for the profile
  (needs only the Place ID, no API key).
* ``fetch_google_reviews`` — rating, number of reviews and up to 5 reviews from
  the Places API (New), shown live on the site.

Google's rules followed here (Places API policies):
* reviews are fetched live and only kept in a short cache (no copy is stored in
  the database); the Place ID itself may be stored indefinitely;
* every review shows its author (photo, name, profile link) and a link to the
  review on Google Maps, inside a visually separate "Google" block;
* translated reviews are flagged; the page explains that Google does not verify
  reviews and that they are sorted by relevance.
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

PLACES_URL = "https://places.googleapis.com/v1/places/{place_id}"
FIELD_MASK = "rating,userRatingCount,reviews,googleMapsUri"
CACHE_SECONDS = 60 * 60  # 1 hour: keeps API usage low without storing reviews
GOOGLE_LANG = {"pt-br": "pt-BR", "en": "en", "es": "es"}


def write_review_url(place_id):
    if not place_id:
        return ""
    return "https://search.google.com/local/writereview?" + urllib.parse.urlencode({"placeid": place_id})


def _clean_review(raw, lang):
    text = (raw.get("text") or {})
    original = (raw.get("originalText") or {})
    author = raw.get("authorAttribution") or {}
    shown = text.get("text") or original.get("text") or ""
    if not shown:
        return None
    translated = bool(text.get("languageCode") and original.get("languageCode")
                      and text["languageCode"].split("-")[0] != original["languageCode"].split("-")[0])
    return {
        "author": author.get("displayName") or "",
        "author_url": author.get("uri") or "",
        "author_photo": author.get("photoUri") or "",
        "rating": int(raw.get("rating") or 0),
        "text": shown,
        "translated": translated,
        "when": raw.get("relativePublishTimeDescription") or "",
        "url": raw.get("googleMapsUri") or author.get("uri") or "",
    }


def fetch_google_reviews(place_id, lang="pt-br"):
    """Returns a dict or None (not configured / Google unavailable). Never raises."""
    api_key = getattr(settings, "GOOGLE_PLACES_API_KEY", "")
    if not (place_id and api_key):
        return None
    key = f"google-reviews:{place_id}:{lang}"
    cached = cache.get(key)
    if cached is not None:
        return cached or None
    url = PLACES_URL.format(place_id=urllib.parse.quote(place_id, safe="")) + "?" + urllib.parse.urlencode(
        {"languageCode": GOOGLE_LANG.get(lang, "en")})
    request = urllib.request.Request(url, headers={
        "X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELD_MASK, "User-Agent": "TravelPipa/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        logger.error("Google Places error %s: %s", exc.code, exc.read()[:300])
        cache.set(key, {}, 10 * 60)  # do not hammer the API while misconfigured
        return None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        logger.exception("Could not reach Google Places")
        cache.set(key, {}, 5 * 60)
        return None
    reviews = [r for r in (_clean_review(raw, lang) for raw in data.get("reviews") or []) if r]
    result = {
        "rating": data.get("rating"),
        "count": data.get("userRatingCount") or 0,
        "maps_url": data.get("googleMapsUri") or "",
        "reviews": reviews,
    }
    cache.set(key, result, CACHE_SECONDS)
    return result
