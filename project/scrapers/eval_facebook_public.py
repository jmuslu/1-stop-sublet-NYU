from __future__ import annotations

from scrapers.base import SourceConfig
from scrapers.sources.facebook_manual import FacebookManualScraper


def make_scraper() -> FacebookManualScraper:
    return FacebookManualScraper(
        SourceConfig(
            name="Facebook",
            enabled=True,
            vetted_users=False,
            config={
                "group_url": "https://www.facebook.com/groups/838592299562056/",
                "default_date": "2026-06-19",
                "default_location": "New York, NY",
                "location_terms": ["East Village", "Greenwich Village"],
                "strong_offer_terms": ["private room available", "sublet available"],
                "offer_terms": ["available"],
                "include_terms": ["room", "sublet"],
                "seeker_terms": ["looking for a sublet"],
                "exclude_terms": [],
                "question_terms": [],
            },
        )
    )


def main() -> None:
    scraper = make_scraper()
    escaped_text = (
        r"\ud83c\udfe1 Private Room Available in East Village \u2013 Girls Only "
        r"$1,200/month from June 15 through August 31"
    )
    page = (
        '{"actors":[{"__typename":"User","name":"Harini Thiru","short_name":"Harini"}],'
        '"post_id":"2085852295649504","story":{"message":{"text":"'
        + escaped_text
        + r'"}},'
        r'"image":{"uri":"https:\/\/scontent-lga3-1.xx.fbcdn.net\/v\/photo.jpg"}}'
        '{"actors":[{"__typename":"User","name":"Harini Thiru","short_name":"Harini"}],'
        '"post_id":"2085852295649504","story":{"message":{"text":"duplicate should be ignored"}}'
    )

    posts = scraper._extract_public_posts(page)
    assert len(posts) == 1, posts
    assert posts[0]["author"] == "Harini Thiru"
    assert posts[0]["url"].endswith("/posts/2085852295649504/")
    assert "Private Room Available" in posts[0]["text"]
    assert posts[0]["imageUrls"] == ["https://scontent-lga3-1.xx.fbcdn.net/v/photo.jpg"]

    listing = scraper._normalize_post(scraper._coerce_post(posts[0]))
    assert listing is not None
    assert listing.price == 1200
    assert listing.location == "East Village, New York, NY"
    assert listing.availabilityLabel == "June 15 through August 31"

    assert scraper._extract_public_posts("<html>Log in to Facebook</html>") == []
    print("PASS Facebook public parser edge cases")


if __name__ == "__main__":
    main()
