from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from scrapers.registry import load_sources
from scrapers.title_generator import generate_titles

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "src" / "data" / "generatedListings.json"

# How long a listing stays in the aggregate after we first saw it. Reddit's
# search feed only ever exposes a rolling window of ~100 posts per query, so
# without accumulation the site can never show more than that window - and a
# listing silently vanishes the moment it scrolls out. Accumulating past the
# window is what makes the feed worth reading; this cutoff is what stops it
# turning into an archive of dead 2023 posts.
MAX_AGE_DAYS = int(os.environ.get("LISTING_MAX_AGE_DAYS", "180"))


def main() -> None:
    existing = _load_existing()
    existing_by_platform = _group_by_platform(existing)

    scraped_by_url: dict[str, dict] = {}
    for scraper in load_sources():
        scraped = [listing.to_json() for listing in scraper.scrape()]
        if not scraped and existing_by_platform.get(scraper.source.name):
            print(f"Warning: {scraper.source.name} returned nothing; keeping its existing listings")
            continue
        for listing in scraped:
            url = listing.get("sourceUrl")
            if url and url not in scraped_by_url:
                scraped_by_url[url] = listing

    merged = _merge(existing, scraped_by_url)
    fresh, dropped = _prune(merged)

    if not fresh:
        if OUTPUT_PATH.exists():
            print(f"Warning: no listings after merge; keeping existing {OUTPUT_PATH}")
            return
        print("Warning: no listings scraped and no existing file to keep")
        return

    generate_titles(fresh)
    fresh.sort(key=lambda listing: listing["dateListed"], reverse=True)
    OUTPUT_PATH.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")

    added = len(set(scraped_by_url) - _urls(existing))
    print(
        f"Wrote {len(fresh)} listings to {OUTPUT_PATH} "
        f"({len(scraped_by_url)} scraped this run, {added} new, {dropped} aged out)"
    )


def _merge(existing: list[dict], scraped_by_url: dict[str, dict]) -> list[dict]:
    """Union previously stored listings with this run's, keyed by sourceUrl.

    A freshly scraped copy wins on every field except ``dateListed``, which
    keeps the earlier value. That preserves a stable first-seen date, so
    sources that don't publish a post date (their index just shows what is
    live now) don't reset to "today" on every rebuild and sit permanently at
    the top of the feed.
    """
    merged: dict[str, dict] = {}

    for listing in existing:
        url = listing.get("sourceUrl")
        if url:
            merged[url] = listing

    for url, listing in scraped_by_url.items():
        previous = merged.get(url)
        if previous is None:
            merged[url] = listing
            continue
        combined = dict(listing)
        first_seen = min(
            filter(None, [previous.get("dateListed"), listing.get("dateListed")]),
            default=listing.get("dateListed"),
        )
        combined["dateListed"] = first_seen
        merged[url] = combined

    return list(merged.values())


def _prune(listings: list[dict]) -> tuple[list[dict], int]:
    """Drop listings that are too old or whose sublet window already ended."""
    today = date.today()
    cutoff = today - timedelta(days=MAX_AGE_DAYS)
    kept: list[dict] = []
    dropped = 0

    for listing in listings:
        listed = _parse_date(listing.get("dateListed"))
        if listed is not None and listed < cutoff:
            dropped += 1
            continue
        available_to = _parse_date(listing.get("availableTo"))
        if available_to is not None and available_to < today:
            dropped += 1
            continue
        kept.append(listing)

    return kept, dropped


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _urls(listings: list[dict]) -> set[str]:
    return {item.get("sourceUrl") for item in listings if item.get("sourceUrl")}


def _load_existing() -> list[dict]:
    if not OUTPUT_PATH.exists():
        return []
    try:
        existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(existing, list):
        return []
    return [item for item in existing if isinstance(item, dict)]


def _group_by_platform(listings: list[dict]) -> dict[str, list[dict]]:
    by_platform: dict[str, list[dict]] = {}
    for listing in listings:
        platform = listing.get("platform")
        if isinstance(platform, str):
            by_platform.setdefault(platform, []).append(listing)
    return by_platform


if __name__ == "__main__":
    main()
