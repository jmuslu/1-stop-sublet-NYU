from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

from scrapers.base import ListingScraper, NormalizedListing

_ID_RE = re.compile(r'href="/listings/([a-f0-9]{24})"')
_IMG_RE = re.compile(r'src="(https://subletr-prod[^"]+)"')
_SVG_RE = re.compile(r"<svg[\s\S]*?</svg>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_LEAD_RE = re.compile(r'^href="[^"]*"[^>]*>\s*')
_RESERVED_RE = re.compile(r"^Reserved\s+", re.IGNORECASE)

# Subletr lists campuses nationwide, so a listing whose state is not in
# ``states`` (or whose city is not in ``cities``) is dropped — this is what keeps
# out-of-area listings out of the feed. Both come from the source's JSON config so
# the same scraper serves any campus; these are the NYU-area defaults.
_DEFAULT_STATES = ("NY", "NJ")
_DEFAULT_CITIES = (
    # Manhattan
    "Greenwich Village",
    "West Village",
    "East Village",
    "Lower East Side",
    "Financial District",
    "Hell's Kitchen",
    "Upper East Side",
    "Upper West Side",
    "Murray Hill",
    "Union Square",
    "Morningside Heights",
    "Washington Heights",
    "Kips Bay",
    "Gramercy",
    "Chinatown",
    "Flatiron",
    "Tribeca",
    "Chelsea",
    "Nolita",
    "Harlem",
    "NoHo",
    "SoHo",
    "Manhattan",
    # Brooklyn
    "Downtown Brooklyn",
    "Bedford-Stuyvesant",
    "Brooklyn Heights",
    "Prospect Heights",
    "Crown Heights",
    "Williamsburg",
    "Fort Greene",
    "Greenpoint",
    "Park Slope",
    "Bushwick",
    "DUMBO",
    "Brooklyn",
    # Queens + nearby
    "Long Island City",
    "Sunnyside",
    "Astoria",
    "Queens",
    "Jersey City",
    "Hoboken",
    "New York",
)


class SubletrScraper(ListingScraper):
    """Subletr (https://www.subletr.com) — a student-to-student sublet marketplace.

    Subletr is a Next.js app that server-renders its public ``/listings`` index, so
    every active card (school, city, term, beds/baths, price, post date, blurb, and
    photo) is present in the initial HTML with no API key or sign-in required. Posting
    a listing requires a verified student account, which is why ``vetted_users`` is
    true: every lister is a verified student.

    Follows the same contract/fallback pattern as the Reddit scraper: any network or
    parsing failure prints a warning and returns ``[]`` so the build stays green and
    the previously generated data is kept.
    """

    def scrape(self) -> list[NormalizedListing]:
        cfg = self.source.config
        url = cfg.get("listings_url", "https://www.subletr.com/listings")
        max_items = int(cfg.get("max_items", 100))

        try:
            page = self._fetch(url)
        except urllib.error.URLError as exc:
            print(f"Warning: could not fetch {self.source.name}: {exc}")
            return []

        listings: list[NormalizedListing] = []
        for listing in self._parse(page):
            listings.append(listing)
            if len(listings) >= max_items:
                break
        return listings

    def _fetch(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.source.config.get(
                    "user_agent",
                    "Mozilla/5.0 1StopSublet/0.1 (housing aggregation)",
                ),
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", "replace")

    def _parse(self, page: str) -> list[NormalizedListing]:
        matches = list(_ID_RE.finditer(page))
        site = self.source.config.get("site_url", "https://www.subletr.com").rstrip("/")
        results: list[NormalizedListing] = []
        seen: set[str] = set()
        for index, match in enumerate(matches):
            listing_id = match.group(1)
            if listing_id in seen:
                continue
            seen.add(listing_id)
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(page)
            listing = self._normalize(listing_id, page[start:end], site)
            if listing is not None:
                results.append(listing)
        return results

    def _normalize(self, listing_id: str, segment: str, site: str) -> NormalizedListing | None:
        text = self._segment_text(segment)
        head = re.match(r"(.+?)\s*,\s*([A-Z]{2})\s+(.+?)\s+\d+\s*guest", text)
        if head is None:
            return None

        place = head.group(1).strip()
        state = head.group(2)
        term = head.group(3).strip()

        school, city = self._split_place(place, state)
        if city is None:
            # Outside the configured area (e.g., other-state campuses) — skip it.
            return None

        description = self._description(text)

        return NormalizedListing(
            id=f"subletr-{listing_id}",
            title=self._trim(self._title(description, term, city), 80),
            description=self._trim(description, 280),
            price=self._price(text),
            location=f"{city}, {state.upper()}",
            bedrooms=self._beds(text),
            bathrooms=self._baths(text),
            platform=self.source.name,
            dateListed=self._date(text),
            imageUrl=self._image(segment),
            sourceUrl=f"{site}/listings/{listing_id}",
            sourceVettedUsers=self.source.vetted_users,
            school=school,
            amenities=self._amenities(term, description),
            applianceNotes=self._term_note(term),
        )

    def _split_place(self, place: str, state: str) -> tuple[str | None, str | None]:
        """Split Subletr's "{School} {City}" label into (school, city).

        Returns ``(None, None)`` when the listing is outside the configured area,
        which is the signal the caller uses to drop out-of-area listings.
        """
        states = self.source.config.get("states", _DEFAULT_STATES)
        if state.upper() not in {s.upper() for s in states}:
            return None, None
        for city in self.source.config.get("cities", _DEFAULT_CITIES):
            match = re.search(rf"\b{re.escape(city)}\s*$", place, re.IGNORECASE)
            if match:
                school = place[: match.start()].strip(" ,")
                return (school or None), city
        return None, None

    def _segment_text(self, segment: str) -> str:
        cleaned = _SVG_RE.sub(" ", segment)
        cleaned = _TAG_RE.sub(" ", cleaned)
        cleaned = html.unescape(re.sub(r"\s+", " ", cleaned)).strip()
        cleaned = _LEAD_RE.sub("", cleaned)
        return _RESERVED_RE.sub("", cleaned).strip()

    def _description(self, text: str) -> str:
        match = re.search(r"bathroom\s+(.*?)\s+\$\s*[\d,]+\s*/\s*month", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r"bathroom\s+(.*?)\s+Posted\s", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r"bathroom\s+(.*)$", text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _price(self, text: str) -> int | None:
        match = re.search(r"\$\s*([\d,]+)\s*/\s*month", text)
        if not match:
            return None
        try:
            return int(match.group(1).replace(",", ""))
        except ValueError:
            return None

    def _beds(self, text: str) -> int:
        match = re.search(r"(\d+)\s*beds?\b", text, re.IGNORECASE)
        return int(match.group(1)) if match else 1

    def _baths(self, text: str) -> float:
        match = re.search(r"(\d+(?:\.5)?)\s*bathroom", text, re.IGNORECASE)
        return float(match.group(1)) if match else 1.0

    def _date(self, text: str) -> str:
        match = re.search(r"Posted\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})", text)
        if not match:
            return "1970-01-01"
        try:
            return datetime.strptime(match.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            return "1970-01-01"

    def _image(self, segment: str) -> str:
        match = _IMG_RE.search(segment)
        if match:
            return match.group(1)
        return self.source.config.get("default_image_url", "")

    def _amenities(self, term: str, description: str) -> list[str]:
        amenities = ["Subletr"]
        if term:
            amenities.append(term)
        lowered = description.lower()
        keyword_labels = {
            "furnished": "Furnished",
            "laundry": "Laundry",
            "parking": "Parking",
            "gym": "Gym",
            "utilities included": "Utilities included",
            "private": "Private room",
            "pet": "Pet friendly",
        }
        for keyword, label in keyword_labels.items():
            if keyword in lowered and label not in amenities:
                amenities.append(label)
        return amenities[:8]

    def _term_note(self, term: str) -> str | None:
        return f"Available {term}" if term else None

    def _title(self, description: str, term: str, city: str) -> str:
        sentence = self._first_sentence(description)
        if len(sentence) >= 12:
            return sentence.rstrip(" .!?,")
        parts = [part for part in (term, "Sublet", f"in {city}") if part]
        return " ".join(parts)

    def _first_sentence(self, description: str) -> str:
        chunks = [c.strip() for c in re.split(r"(?<=[.!?])\s+|\n+", description) if c.strip()]
        # Prefer a substantive sentence that starts like a real one (capital/number)
        # and is not a bare greeting, mirroring the Reddit scraper's title logic.
        for cleaned in chunks:
            if len(cleaned) < 15 or self._is_greeting(cleaned):
                continue
            if cleaned[0].isupper() or cleaned[0].isdigit():
                return cleaned
        for cleaned in chunks:
            if len(cleaned) >= 12 and not self._is_greeting(cleaned):
                return cleaned
        return description.strip()

    def _is_greeting(self, text: str) -> bool:
        return bool(re.match(r"(hi|hey|hello|hiya|yo)\b[\s,!.]*$", text, re.IGNORECASE)) or bool(
            re.match(r"(hi|hey|hello)\s+(everyone|all|there|guys|y'?all)\b[\s,!.]*$", text, re.IGNORECASE)
        )

    def _trim(self, value: str, limit: int) -> str:
        normalized = re.sub(r"\s+", " ", value or "").strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 1].rstrip() + "…"
