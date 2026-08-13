from __future__ import annotations

from dataclasses import dataclass

from scrapers.registry import load_sources
from scrapers.sources.reddit import RedditThreadScraper


@dataclass(frozen=True)
class Case:
    name: str
    text: str
    has_images: bool
    expected_intent: str
    expected_price: int | None = None
    expected_availability: str | None = None
    expected_location: str | None = None
    expected_bedrooms: int | None = None
    expected_bathrooms: float | None = None


CASES = [
    Case(
        name="offer_my_furnished_room_with_question",
        text=(
            "Hey, I'm looking for a sublet for my furnished room the rest of the summer: "
            "- June 15th through August 31st (flexible with timeline) "
            "- $1,000/month, utilities included (1GB/s Fios internet) "
            "- Central AC, in-unit laundry, hardwood floors "
            "- Two blocks from Washington Square. It's a furnished room in a 6 bed / 3 bath "
            "apartment on Bleecker St in Greenwich Village. DM me if you're interested?"
        ),
        has_images=True,
        expected_intent="offer",
        expected_price=1000,
        expected_availability="June 15th through August 31st",
        expected_location="Greenwich Village, New York, NY",
    ),
    Case(
        name="image_only_reply",
        text="https://preview.redd.it/927bi96y4x5h1.jpeg?width=4032&format=pjpg living room",
        has_images=True,
        expected_intent="seeker",
    ),
    Case(
        name="seeker_looking_for_room",
        text="Incoming grad student looking for a studio near campus. Looking to spend $2500.",
        has_images=False,
        expected_intent="seeker",
        expected_price=2500,
    ),
    Case(
        name="question_about_lease",
        text="I applied for Broome Street but the lease says 8/2025-8/2027. Does that mean I rent for an entire year?",
        has_images=False,
        expected_intent="question",
    ),
    Case(
        name="offer_subletting_room",
        text="Subletting a room in 3B/1B right by Washington Square for 900$ + utilities from 8th August - 31 August.",
        has_images=False,
        expected_intent="offer",
        expected_price=900,
    ),
    Case(
        name="offer_take_over_lease",
        text="My roommate and I are looking for 2 students to take over our Third North lease July 1 to August 14 for $1600.",
        has_images=True,
        expected_intent="offer",
        expected_price=1600,
        expected_availability="July 1 to August 14",
    ),
    Case(
        name="offer_roommate_opening_with_unit_details",
        text=(
            "LOOKING FOR A ROOMMATE "
            "Mixed gender group looking to sign on a yearly lease. Our fourth ghosted us "
            "but the rent is 1475. Place is 7 min away from the L train. Only requirement "
            "is to keep communal areas clean. You can invite over whoever you want but a "
            "heads up to everyone would be nice. 4 bed, 3 bath kitchen has dishwasher and "
            "in unit laundry. Would like to meet prior to signing lease. If interested "
            "please text 2017499877"
        ),
        has_images=False,
        expected_intent="offer",
        expected_price=1475,
        expected_bedrooms=4,
        expected_bathrooms=3.0,
    ),
    Case(
        name="seeker_roommate_group",
        text="I am an upcoming sophomore looking for girls to join my roommate group for next year.",
        has_images=False,
        expected_intent="seeker",
    ),
    Case(
        name="seeker_roommate_search_without_unit",
        text="Looking for a roommate to search for apartments with next fall. Budget is around $1500.",
        has_images=False,
        expected_intent="seeker",
        expected_price=1500,
    ),
    Case(
        name="non_listing_student_assumption",
        text="Hi assuming everyone here are NYU students. Fill out this form for housing interest.",
        has_images=True,
        expected_intent="seeker",
    ),
]


def main() -> None:
    scraper = next(source for source in load_sources() if isinstance(source, RedditThreadScraper))
    failures: list[str] = []

    for case in CASES:
        intent = scraper._classify_intent_with_rules(case.text, case.has_images)
        price = scraper._extract_price(case.text)
        availability = scraper._extract_availability(case.text)["label"]
        location = scraper._extract_location(case.text)
        bedrooms = scraper._extract_bedrooms(case.text)
        bathrooms = scraper._extract_bathrooms(case.text)

        if intent != case.expected_intent:
            failures.append(f"{case.name}: intent {intent!r} != {case.expected_intent!r}")
        if case.expected_price is not None and price != case.expected_price:
            failures.append(f"{case.name}: price {price!r} != {case.expected_price!r}")
        if case.expected_availability is not None and availability != case.expected_availability:
            failures.append(
                f"{case.name}: availability {availability!r} != {case.expected_availability!r}"
            )
        if case.expected_location is not None and location != case.expected_location:
            failures.append(f"{case.name}: location {location!r} != {case.expected_location!r}")
        if case.expected_bedrooms is not None and bedrooms != case.expected_bedrooms:
            failures.append(f"{case.name}: bedrooms {bedrooms!r} != {case.expected_bedrooms!r}")
        if case.expected_bathrooms is not None and bathrooms != case.expected_bathrooms:
            failures.append(f"{case.name}: bathrooms {bathrooms!r} != {case.expected_bathrooms!r}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        raise SystemExit(1)

    print(f"PASS {len(CASES)} Reddit rule edge cases")


if __name__ == "__main__":
    main()
