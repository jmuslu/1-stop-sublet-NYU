from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from datetime import datetime

from scrapers.base import ListingScraper, NormalizedListing

_CARD_SPLIT_RE = re.compile(r'(?=<a target="_blank" href="/listings/)')
_SLUG_RE = re.compile(r'href="(/listings/[^"#?]+)"')
_IMG_RE = re.compile(r'src="(https://listing-photos\.[^"]+?)"')
_PRICE_RE = re.compile(r"\$([\d,]+)\s*/\s*month", re.IGNORECASE)
_DATES_RE = re.compile(
    r">\s*([A-Z][a-z]+ \d{1,2}, \d{4})\s*-\s*([A-Z][a-z]+ \d{1,2}, \d{4})\s*<"
)
_PLACE_RE = re.compile(r'style="word-wrap: break-word;">\s*([^<|]+?)\s*\|\s*([^<]+?)\s*</div>')
_TITLE_RE = re.compile(r'href="/listings/[^"]+">([^<]{3,200})</a>\s*</h4>')
_BODY_RE = re.compile(r'<p class="text-sm leading-normal mb-4"[^>]*>(.*?)</p>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")


class ListingsProjectScraper(ListingScraper):
    """Listings Project (https://www.listingsproject.com) NYC sublets index.

    A weekly-curated New York listing service. Its public
    ``/real-estate/new-york-city/sublets`` index is server-rendered, so each card
    (title, neighborhood, price, date range, blurb, and photo) is in the initial
    HTML with no API key or sign-in. The public index is a preview of the
    newsletter, so expect roughly a dozen listings rather than hundreds.

    Listers are not student-verified - this is a general NYC audience - so
    ``vetted_users`` is false and the feed ranks these below NYU-tagged posts.

    Follows the same contract/fallback pattern as the other scrapers: any network
    or parsing failure prints a warning and returns ``[]`` so the build stays
    green and previously generated data is kept.
    """

    def scrape(self) -> list[NormalizedListing]:
        cfg = self.source.config
        url = cfg.get("listings_url", "https://www.listingsproject.com/real-estate/new-york-city/sublets")
        site = cfg.get("site_url", "https://www.listingsproject.com").rstrip("/")
        max_items = int(cfg.get("max_items", 100))

        try:
            page = self._fetch(url)
        except urllib.error.URLError as exc:
            print(f"Warning: could not fetch {self.source.name}: {exc}")
            return []

        listings: list[NormalizedListing] = []
        seen: set[str] = set()
        for card in _CARD_SPLIT_RE.split(page):
            listing = self._normalize(card, site)
            if listing is None or listing.sourceUrl in seen:
                continue
            seen.add(listing.sourceUrl)
            listings.append(listing)
            if len(listings) >= max_items:
                break

        if not listings:
            print(f"Warning: {self.source.name} returned no listings; markup may have changed")
        return listings

    def _fetch(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.source.config.get(
                    "user_agent",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
                ),
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")

    def _normalize(self, card: str, site: str) -> NormalizedListing | None:
        slug = _SLUG_RE.search(card)
        title = _TITLE_RE.search(card)
        if slug is None or title is None:
            return None

        place = _PLACE_RE.search(card)
        if place is None:
            return None
        neighborhood, category = place.group(1).strip(), place.group(2).strip()
        # The index mixes sublets with wanted-ads and shares; keep only sublets.
        if "sublet" not in category.lower():
            return None

        available_from, available_to = self._dates(card)
        price_match = _PRICE_RE.search(card)
        body = _BODY_RE.search(card)
        description = self._text(body.group(1)) if body else ""
        description = re.sub(r"\s*See more\s*$", "", description).strip()

        return NormalizedListing(
            id=f"listingsproject-{slug.group(1).rsplit('-', 1)[-1][:24]}",
            title=self._text(title.group(1))[:80],
            description=description[:280],
            price=int(price_match.group(1).replace(",", "")) if price_match else None,
            location=self._location(neighborhood),
            bedrooms=self._beds(title.group(1), description),
            bathrooms=1.0,
            platform=self.source.name,
            dateListed=datetime.now().strftime("%Y-%m-%d"),
            imageUrl=self._image(card),
            sourceUrl=f"{site}{slug.group(1)}",
            sourceVettedUsers=self.source.vetted_users,
            availabilityLabel=self._availability_label(available_from, available_to),
            availableFrom=available_from,
            availableTo=available_to,
        )

    def _location(self, neighborhood: str) -> str:
        """Turn "Prospect Heights, Brooklyn" into the app's location shape."""
        default = self.source.config.get("default_location", "New York, NY")
        head = neighborhood.split(",")[0].strip().lower()
        if not head:
            return default
        overrides = self.source.config.get("location_suffix_overrides", {})
        # Listings Project writes compound areas like "Prospect Heights/North
        # Park Slope", so match on containment. Longest term first, otherwise
        # "Park Slope" would win over the more specific "Prospect Heights".
        known = sorted(self.source.config.get("location_terms", []), key=len, reverse=True)
        for term in known:
            if term.lower() in head:
                return f"{term}, {overrides.get(term, 'New York, NY')}"
        return default

    def _dates(self, card: str) -> tuple[str | None, str | None]:
        match = _DATES_RE.search(card)
        if match is None:
            return None, None
        return self._iso(match.group(1)), self._iso(match.group(2))

    def _iso(self, value: str) -> str | None:
        try:
            return datetime.strptime(value, "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _availability_label(self, start: str | None, end: str | None) -> str | None:
        if start and end:
            return f"{start} to {end}"
        return start or end

    def _beds(self, title: str, description: str) -> int:
        text = f"{title} {description}".lower()
        if re.search(r"\bstudio\b", text):
            return 0
        match = re.search(r"\b([1-6])\s?(?:bed|beds|bedroom|bedrooms|br)\b", text)
        return int(match.group(1)) if match else 1

    def _image(self, card: str) -> str | None:
        match = _IMG_RE.search(card)
        return html.unescape(match.group(1)) if match else None

    def _text(self, raw: str) -> str:
        return re.sub(r"\s+", " ", html.unescape(_TAG_RE.sub(" ", raw))).strip()
