from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser

from scrapers.base import ListingScraper, NormalizedListing

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
MONTH_PATTERN = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?"
)


@dataclass(frozen=True)
class RedditFeedEntry:
    index: int
    link: str
    author: str | None
    date: str
    content: str
    image_urls: list[str]
    # Post title. Empty for megathread comments (they have none); set for
    # standalone posts, where the title carries most of the intent signal.
    title: str = ""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.image_urls: list[str] = []
        self.link_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "img" and values.get("src"):
            self.image_urls.append(values["src"])
        if tag == "a" and values.get("href"):
            self.link_urls.append(values["href"])

    def handle_data(self, data: str) -> None:
        cleaned = data.strip()
        if cleaned:
            self.parts.append(cleaned)

    def text(self) -> str:
        return " ".join(self.parts)


class RedditThreadScraper(ListingScraper):
    def scrape(self) -> list[NormalizedListing]:
        max_items = int(self.source.config.get("max_items", 75))
        # Search feeds have no originating thread to skip, so this is optional.
        thread_url = self.source.config.get("thread_url", "").rstrip("/")

        entries = self._gather_entries(thread_url)
        if not entries:
            return []

        thread_title = self.source.config.get("thread_title", "Housing megathread")
        subreddit = self.source.config.get("subreddit", "r/nyu")
        photo_attach_window = int(self.source.config.get("photo_attach_window", 8))

        photo_entries = [entry for entry in entries if entry.image_urls]
        listings: list[NormalizedListing] = []
        seen_listing_keys: set[str] = set()
        seen_listing_slots: set[str] = set()
        seen_author_fingerprints: dict[str, list[set[str]]] = {}
        for entry in entries:
            # Everything is read off _analysis_text so a subclass can fold the post
            # title in; the description below stays the untouched body text.
            text = self._analysis_text(entry)
            intent = self._entry_intent(entry, text)
            if intent != "offer":
                continue

            price = self._extract_price(text)
            location = self._extract_location(text)
            bedrooms = self._extract_bedrooms(text)
            bathrooms = self._extract_bathrooms(text)
            title = self._entry_title(entry, price, location)
            amenities = self._extract_amenities(text, subreddit, thread_title)
            attached_images = self._images_for_entry(entry, photo_entries, photo_attach_window)
            availability = self._extract_availability(text)
            listing_key = self._listing_key(entry.author, title)
            if listing_key in seen_listing_keys:
                continue
            slot_key = self._listing_slot_key(entry.author, price, location, availability["label"])
            if slot_key and slot_key in seen_listing_slots:
                continue
            fingerprint = self._listing_fingerprint(text)
            if self._is_near_duplicate(entry.author, fingerprint, seen_author_fingerprints):
                continue
            seen_listing_keys.add(listing_key)
            if slot_key:
                seen_listing_slots.add(slot_key)
            seen_author_fingerprints.setdefault(entry.author or "", []).append(fingerprint)

            listings.append(
                NormalizedListing(
                    id=f"reddit-{entry.link.rstrip('/').split('/')[-1]}",
                    title=title,
                    description=self._trim(entry.content, 280),
                    price=price,
                    location=location,
                    bedrooms=bedrooms,
                    bathrooms=bathrooms,
                    platform=self.source.name,
                    dateListed=entry.date,
                    imageUrl=attached_images[0] if attached_images else None,
                    imageUrls=attached_images,
                    sourceUrl=entry.link,
                    sourceVettedUsers=self.source.vetted_users,
                    sourceSubreddit=subreddit,
                    sourceThreadTitle=thread_title,
                    sourceAuthor=entry.author,
                    sourceIntent=intent,
                    availabilityLabel=availability["label"],
                    availableFrom=availability["from"],
                    availableTo=availability["to"],
                    termTags=availability["tags"],
                    amenities=amenities,
                    roommatesTotal=self._extract_roommates(text),
                    parking=self._extract_parking(text),
                    extraCosts=self._extract_extra_costs(text),
                    utilitiesNotes=self._extract_utilities(text),
                )
            )

            if len(listings) >= max_items:
                break

        return listings

    def _feed_urls(self) -> list[str]:
        """Every feed this source reads.

        Reddit's search Atom feed returns at most 100 entries and offers no
        pagination, so a single query is a hard ceiling on how much of a
        subreddit we can ever see. Listing several queries (and several
        subreddits) under one source is the only way past it.
        """
        urls = self.source.config.get("feed_urls")
        if urls:
            return list(urls)
        single = self.source.config.get("feed_url")
        return [single] if single else []

    def _gather_entries(self, thread_url: str) -> list[RedditFeedEntry]:
        """Fetch every feed and merge, de-duplicating posts by permalink.

        One feed failing (Reddit 429s aggressively per IP) must not lose the
        others, so each is caught individually. Entries are re-indexed across
        the merged list to keep the photo-attachment window deterministic.
        """
        delay = float(self.source.config.get("request_delay_seconds", 2.0))
        merged: list[RedditFeedEntry] = []
        seen_links: set[str] = set()
        urls = self._feed_urls()

        for position, url in enumerate(urls):
            if position and delay > 0:
                time.sleep(delay)
            try:
                root = ET.fromstring(self._fetch(url))
            except (urllib.error.URLError, ET.ParseError, ValueError) as exc:
                print(f"Warning: could not fetch {self.source.name} feed {url}: {exc}")
                continue
            for entry in self._feed_entries(root, thread_url):
                if entry.link in seen_links:
                    continue
                seen_links.add(entry.link)
                merged.append(entry)

        if not merged:
            print(f"Warning: {self.source.name} returned no entries from {len(urls)} feed(s)")
            return []

        print(f"{self.source.name}: {len(merged)} unique posts from {len(urls)} feed(s)")
        return [
            RedditFeedEntry(
                index=index,
                link=entry.link,
                author=entry.author,
                date=entry.date,
                content=entry.content,
                image_urls=entry.image_urls,
                title=entry.title,
            )
            for index, entry in enumerate(merged)
        ]

    def _analysis_text(self, entry: RedditFeedEntry) -> str:
        """Text the extractors and the intent classifier read.

        Megathread comments have no title, so this is just the body. The search
        scraper folds the post title in, because for a standalone post the title
        is where "subletting my room" vs "looking for a room" actually lives.
        """
        return entry.content

    def _entry_title(self, entry: RedditFeedEntry, price: int | None, location: str) -> str:
        return self._build_title(entry.content, price, location, entry.author)

    def _entry_intent(self, entry: RedditFeedEntry, text: str) -> str:
        return self._classify_intent(text, has_images=bool(entry.image_urls))

    def _fetch(self, url: str) -> str:
        """GET a feed, retrying on Reddit's 429s with exponential backoff.

        Reddit rate-limits hard per IP and returns 429 rather than throttling,
        so a burst of feed reads will lose most of them without a retry. Only
        429 and 5xx are retried; anything else fails straight through.
        """
        attempts = int(self.source.config.get("fetch_attempts", 4))
        backoff = float(self.source.config.get("fetch_backoff_seconds", 5.0))
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.source.config.get(
                    "user_agent",
                    "Mozilla/5.0 1StopSublet/0.1 (housing aggregation)",
                )
            },
        )

        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return response.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code != 429 and exc.code < 500:
                    raise
                if attempt == attempts - 1:
                    break
                time.sleep(backoff * (2**attempt))
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt == attempts - 1:
                    break
                time.sleep(backoff * (2**attempt))

        raise last_error if last_error else urllib.error.URLError("fetch failed")

    def _feed_entries(self, root: ET.Element, thread_url: str) -> list[RedditFeedEntry]:
        entries: list[RedditFeedEntry] = []
        for index, entry in enumerate(root.findall("atom:entry", ATOM_NS)):
            link = self._entry_link(entry)
            if not link or link.rstrip("/") == thread_url:
                continue
            content, image_urls = self._entry_content(entry)
            entries.append(
                RedditFeedEntry(
                    index=index,
                    link=link,
                    author=self._entry_author(entry),
                    date=self._entry_date(entry),
                    content=content,
                    image_urls=image_urls,
                    title=self._entry_feed_title(entry),
                )
            )
        return entries

    def _entry_feed_title(self, entry: ET.Element) -> str:
        node = entry.find("atom:title", ATOM_NS)
        return html.unescape(node.text).strip() if node is not None and node.text else ""

    def _images_for_entry(
        self,
        entry: RedditFeedEntry,
        photo_entries: list[RedditFeedEntry],
        attach_window: int,
    ) -> list[str]:
        image_urls = list(entry.image_urls)
        for photo_entry in photo_entries:
            if photo_entry.link == entry.link:
                continue
            if photo_entry.author != entry.author:
                continue
            if abs(photo_entry.index - entry.index) > attach_window:
                continue
            if self._classify_intent_with_rules(photo_entry.content, has_images=True) == "offer":
                continue
            for image_url in photo_entry.image_urls:
                if image_url not in image_urls:
                    image_urls.append(image_url)
        return image_urls[:6]

    def _entry_link(self, entry: ET.Element) -> str | None:
        link = entry.find("atom:link", ATOM_NS)
        return link.attrib.get("href") if link is not None else None

    def _entry_author(self, entry: ET.Element) -> str | None:
        node = entry.find("atom:author/atom:name", ATOM_NS)
        return node.text if node is not None else None

    def _entry_date(self, entry: ET.Element) -> str:
        node = entry.find("atom:updated", ATOM_NS)
        if node is None or not node.text:
            return "1970-01-01"
        return node.text[:10]

    def _entry_content(self, entry: ET.Element) -> tuple[str, list[str]]:
        node = entry.find("atom:content", ATOM_NS)
        raw = node.text if node is not None and node.text else ""
        parser = _TextExtractor()
        decoded = html.unescape(raw)
        parser.feed(decoded)
        text = re.sub(r"\s+", " ", parser.text()).strip()
        return text, self._extract_image_urls(decoded, parser)

    def _classify_intent(self, text: str, has_images: bool) -> str:
        deterministic = self._classify_intent_with_rules(text, has_images)
        if deterministic != "unclear":
            return deterministic
        return self._classify_intent_with_gemini(text) or "seeker"

    # Bare possessives ("my room", "our apartment") are common in real listings
    # ("looking for someone to take my room") but also show up in distress posts
    # that are not listings at all ("I just lost my apartment, nowhere to go").
    # Guarded in _matches_strong_offer_terms rather than dropped outright, since
    # dropping them broke far more real listings than it fixed.
    _BARE_STRONG_OFFER_TERMS = frozenset(
        {"my apartment", "my bedroom", "my furnished room", "my place", "my room", "our apartment", "our place"}
    )

    def _classify_intent_with_rules(self, text: str, has_images: bool) -> str:
        lowered = text.lower().replace("’", "'")
        if self._is_image_only_text(lowered):
            return "seeker"
        if self._matches_strong_offer_terms(lowered):
            return "offer"
        if self._contains_config_term(lowered, "question_terms"):
            return "question"
        if self._contains_config_term(lowered, "exclude_terms"):
            return "seeker"
        if self._is_roommate_search_without_unit(lowered):
            return "seeker"
        if self._has_roommate_opening_evidence(lowered):
            return "offer"
        if self._contains_config_term(lowered, "seeker_terms"):
            return "seeker"
        if self._contains_config_term(lowered, "offer_terms"):
            return "offer"
        if self._contains_config_term(lowered, "include_terms"):
            return "unclear"
        return "seeker"

    def _matches_strong_offer_terms(self, lowered_text: str) -> bool:
        """True when a strong_offer_terms entry matches, with a distress guard.

        When the text also reads as a distress/emergency post ("no where to
        go", "lost my apartment"), a bare possessive alone no longer counts -
        it is exactly as likely to mean the writer just lost their home as
        that they are listing it. Verb-qualified terms ("subletting my",
        "lease takeover") still count regardless: "I lost my job and need to
        sublet my apartment ASAP" is still a listing.
        """
        distress = self._contains_config_term(lowered_text, "distress_terms")
        for term in self.source.config.get("strong_offer_terms", []):
            normalized = term.lower().replace("’", "'")
            if distress and normalized in self._BARE_STRONG_OFFER_TERMS:
                continue
            pattern = rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])"
            if re.search(pattern, lowered_text):
                return True
        return False

    def _contains_config_term(self, lowered_text: str, config_key: str) -> bool:
        for term in self.source.config.get(config_key, []):
            normalized = term.lower().replace("’", "'")
            pattern = rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])"
            if re.search(pattern, lowered_text):
                return True
        return False

    def _is_image_only_text(self, lowered_text: str) -> bool:
        without_urls = re.sub(r"https?://\S+", "", lowered_text)
        words = re.findall(r"\b[a-z][a-z]+\b", without_urls)
        return "preview.redd.it" in lowered_text and len(words) <= 4

    def _is_roommate_search_without_unit(self, lowered_text: str) -> bool:
        return bool(
            re.search(r"\blooking for (?:a )?roommate to (?:search|look|find)\b", lowered_text)
            or re.search(r"\broommate group\b", lowered_text)
        )

    # "Looking for a THIRD roommate", "...a NEW roommate" - real posts almost
    # always put a descriptor between the article and "roommate"; a bare
    # "\blooking for (?:a|one|[1-6]) roommate\b" misses all of them.
    _ROOMMATE_DESCRIPTOR = (
        r"(?:new|additional|another|one more|"
        r"1st|2nd|3rd|4th|5th|6th|first|second|third|fourth|fifth|sixth)"
    )

    def _has_roommate_opening_evidence(self, lowered_text: str) -> bool:
        roommate_opening = bool(
            re.search(
                rf"\blooking for (?:a |one |[1-6] )?(?:{self._ROOMMATE_DESCRIPTOR} )?roommate\b",
                lowered_text,
            )
            or re.search(
                rf"\bneed (?:a |one |[1-6] )?(?:{self._ROOMMATE_DESCRIPTOR} )?roommate\b", lowered_text
            )
            or re.search(r"\b(?:one more|[1-6](?:st|nd|rd|th)?) roommate\b", lowered_text)
            or "roommate wanted" in lowered_text
            or "fourth ghosted" in lowered_text
            or "spot left" in lowered_text
        )
        if not roommate_opening:
            return False

        has_price = self._extract_price(lowered_text) is not None
        has_unit_size = bool(
            re.search(r"\b[1-6]\s?(?:bed|beds|bedroom|bedrooms|br)\b", lowered_text)
            and re.search(r"\b[1-4](?:\.5)?\s?(?:bath|baths|bathroom|bathrooms|ba)\b", lowered_text)
        )
        has_existing_unit_signal = bool(
            re.search(r"\b(?:lease|rent|place|unit|apartment|kitchen|laundry|dishwasher)\b", lowered_text)
            or re.search(r"\b(?:orange|green|red|blue)\s+line\b", lowered_text)
        )
        return has_price and has_unit_size and has_existing_unit_signal

    def _classify_intent_with_gemini(self, text: str) -> str | None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None
        prompt = (
            "Classify this Reddit housing megathread comment. "
            "Return exactly one word: offer, seeker, question, or irrelevant. "
            "Use offer only when the writer appears to have a room/unit/spot available. "
            f"Comment: {self._trim(text, 1200)}"
        )
        payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-1.5-flash-latest:generateContent"
            f"?key={api_key}"
        )
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"Warning: Gemini classification skipped: {exc}")
            return None
        text_value = (
            raw.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
            .lower()
        )
        if text_value.startswith("offer"):
            return "offer"
        if text_value.startswith("question"):
            return "question"
        if text_value.startswith("seeker") or text_value.startswith("irrelevant"):
            return "seeker"
        return None

    def _extract_image_urls(self, raw_html: str, parser: _TextExtractor) -> list[str]:
        candidates = parser.image_urls + parser.link_urls
        candidates += re.findall(r"https?://[^\s\"'<>]+", raw_html)
        image_urls: list[str] = []
        for candidate in candidates:
            cleaned = html.unescape(candidate).replace("&amp;", "&")
            if self._is_image_url(cleaned) and cleaned not in image_urls:
                image_urls.append(cleaned)
        return image_urls[:6]

    def _is_image_url(self, url: str) -> bool:
        lowered = url.lower()
        return (
            "preview.redd.it/" in lowered
            or "i.redd.it/" in lowered
            or lowered.endswith((".jpg", ".jpeg", ".png", ".webp"))
        )

    def _listing_key(self, author: str | None, text: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        normalized = re.sub(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "", normalized)
        return f"{author or ''}:{normalized[:90]}"

    def _listing_fingerprint(self, text: str) -> set[str]:
        normalized = text.lower().replace("’", "'")
        normalized = re.sub(r"\$?\b[0-9][0-9,]{1,5}\b(?:\s?\$)?", " ", normalized)
        tokens = set(re.findall(r"\b[a-z][a-z]{3,}\b", normalized))
        stop_words = {
            "apartment",
            "available",
            "please",
            "reach",
            "room",
            "rooms",
            "sublet",
            "subletting",
        }
        return tokens - stop_words

    def _listing_slot_key(
        self,
        author: str | None,
        price: int | None,
        location: str,
        availability_label: str | list[str] | None,
    ) -> str | None:
        if not author or price is None or not availability_label:
            return None
        normalized_availability = re.sub(r"[^a-z0-9]+", " ", str(availability_label).lower()).strip()
        return f"{author}:{price}:{location.lower()}:{normalized_availability}"

    def _is_near_duplicate(
        self,
        author: str | None,
        fingerprint: set[str],
        seen_author_fingerprints: dict[str, list[set[str]]],
    ) -> bool:
        if len(fingerprint) < 6:
            return False
        for existing in seen_author_fingerprints.get(author or "", []):
            overlap = len(fingerprint & existing)
            union = len(fingerprint | existing)
            if union and overlap / union >= 0.48:
                return True
        return False

    def _extract_price(self, text: str) -> int | None:
        patterns = [
            r"\$\s?([0-9][0-9,]{2,5})",
            r"\b([0-9][0-9,]{2,5})\s?\$",
            r"\b(?:rent|budget|price)\D{0,18}([0-9][0-9,]{2,5})\b",
            r"\b([0-9][0-9,]{2,5})\s?(?:/mo|per month|monthly)\b",
        ]
        matches: list[str] = []
        for pattern in patterns:
            matches.extend(re.findall(pattern, text, re.IGNORECASE))
        if not matches:
            return None
        prices = [int(match.replace(",", "")) for match in matches]
        plausible = [price for price in prices if 400 <= price <= 6000]
        return plausible[0] if plausible else None

    def _default_location(self) -> str:
        return self.source.config.get("default_location", "New York, NY")

    def _city_suffix(self) -> str:
        """City/state appended to a matched neighborhood, e.g. "New York, NY"."""
        return self.source.config.get("city_suffix", self._default_location())

    def _extract_location(self, text: str) -> str:
        # Some matched neighborhoods sit outside the default city/state - Jersey
        # City is "Jersey City, NJ", not "Jersey City, New York, NY".
        overrides = self.source.config.get("location_suffix_overrides", {})
        for location in self.source.config.get("location_terms", []):
            if re.search(rf"\b{re.escape(location)}\b", text, re.IGNORECASE):
                return f"{location}, {overrides.get(location, self._city_suffix())}"
        return self._default_location()

    def _extract_bedrooms(self, text: str) -> int:
        patterns = [
            r"\b([1-6])\s?(?:bed|beds|bedroom|bedrooms|br)\b",
            r"\b([1-6])b(?:d|r)?\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        if re.search(r"\bstudio\b", text, re.IGNORECASE):
            return 0
        return 1

    def _extract_bathrooms(self, text: str) -> float:
        match = re.search(r"\b([1-4](?:\.5)?)\s?(?:bath|baths|bathroom|bathrooms|ba)\b", text, re.IGNORECASE)
        return float(match.group(1)) if match else 1

    def _extract_roommates(self, text: str) -> int | None:
        match = re.search(r"\b(?:with|and)\s+([1-6])\s+(?:roommates|people|others)\b", text, re.IGNORECASE)
        if match:
            return int(match.group(1)) + 1
        match = re.search(r"\b([1-6])\s+(?:roommates|people)\b", text, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _extract_parking(self, text: str) -> str | None:
        lowered = text.lower()
        if "parking" not in lowered and "driveway" not in lowered:
            return None
        if "no parking" in lowered:
            return "No parking listed"
        if "driveway" in lowered:
            return "Driveway access"
        return "Parking mentioned"

    def _extract_extra_costs(self, text: str) -> list[str]:
        costs = []
        lowered = text.lower()
        if "utilities" in lowered:
            costs.append("Utilities mentioned")
        if "fee" in lowered:
            costs.append("Fees mentioned")
        return costs

    def _extract_utilities(self, text: str) -> str | None:
        sentence = self._sentence_containing(text, "utilities")
        return self._trim(sentence, 140) if sentence else None

    def _extract_availability(self, text: str) -> dict[str, str | list[str] | None]:
        tags = self._extract_term_tags(text)
        date_range = self._extract_date_range(text)
        if date_range:
            label = date_range
        elif tags:
            label = ", ".join(tags)
        else:
            label = None
        return {
            "label": label,
            "from": None,
            "to": None,
            "tags": tags,
        }

    def _extract_term_tags(self, text: str) -> list[str]:
        lowered = text.lower()
        tags = []
        if re.search(r"\bsummer\s*(?:1|i|a)\b", lowered):
            tags.append("Summer 1")
        if re.search(r"\bsummer\s*(?:2|ii|b)\b", lowered):
            tags.append("Summer 2")
        if "summer" in lowered and not tags:
            tags.append("Summer")
        if "fall" in lowered:
            tags.append("Fall")
        if "spring" in lowered:
            tags.append("Spring")
        return tags

    def _extract_date_range(self, text: str) -> str | None:
        compact = re.sub(r"\s+", " ", text)
        patterns = [
            rf"\b({MONTH_PATTERN})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?\s*(?:-|–|—|to|through|until)\s*({MONTH_PATTERN})?\.?\s*\d{{1,2}}(?:st|nd|rd|th)?\b",
            rf"\b({MONTH_PATTERN})\.?\s*(?:-|–|—|to|through|until)\s*({MONTH_PATTERN})\.?\b",
            rf"\b({MONTH_PATTERN})\.?\s+(?:to|through|until)\s+({MONTH_PATTERN})\.?\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, compact, re.IGNORECASE)
            if match:
                return self._trim(match.group(0), 60)
        return None

    def _extract_amenities(self, text: str, subreddit: str, thread_title: str) -> list[str]:
        amenities = ["Reddit", subreddit]
        lowered = text.lower()
        keyword_labels = {
            "furnished": "Furnished",
            "laundry": "Laundry",
            "parking": "Parking",
            "driveway": "Driveway",
            "gym": "Gym",
            "near": "Near campus",
            "co-op": "Co-op term",
            "sublet": "Sublet",
            "roommate": "Roommate",
        }
        for keyword, label in keyword_labels.items():
            if keyword in lowered and label not in amenities:
                amenities.append(label)
        if thread_title and "Housing megathread" not in amenities:
            amenities.append("Housing megathread")
        return amenities[:6]

    def _build_title(self, text: str, price: int | None, location: str, author: str | None) -> str:
        if price and location != self._default_location():
            neighborhood = location.replace(f", {self._city_suffix()}", "")
            return f"${price:,} housing lead near {neighborhood}"
        title = self._best_title_sentence(text)
        if title:
            return title
        subreddit = self.source.config.get("subreddit", "Reddit")
        return f"Reddit housing lead from {author or subreddit}"

    def _best_title_sentence(self, text: str) -> str:
        generic = {
            "hi",
            "hi!",
            "hi everyone",
            "hi everyone!",
            "hello",
            "hello!",
            "hey",
            "hey!",
            "hey everyone",
            "hey everyone!",
        }
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sentence in sentences:
            cleaned = sentence.strip()
            if cleaned.lower() in generic:
                continue
            if len(cleaned) < 8:
                continue
            return self._trim(cleaned, 72)
        return ""

    def _sentence_containing(self, text: str, term: str) -> str | None:
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            if term.lower() in sentence.lower():
                return sentence
        return None

    def _trim(self, value: str | None, limit: int) -> str:
        if not value:
            return ""
        normalized = re.sub(r"\s+", " ", value).strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 1].rstrip() + "..."
