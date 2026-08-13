from __future__ import annotations

from dataclasses import dataclass

from scrapers.registry import load_sources
from scrapers.sources.reddit import RedditFeedEntry
from scrapers.sources.reddit_search import RedditSearchScraper


@dataclass(frozen=True)
class Case:
    name: str
    title: str
    body: str
    expected_intent: str
    expected_title: str | None = None
    expected_location: str | None = None


# Titles and bodies below are shortened from real r/nyu posts. The seeker cases
# are the ones that matter: each has a body full of offer vocabulary, so reading
# the body alone files them as sublets that do not exist.
CASES = [
    Case(
        name="seeker_title_with_offer_words_in_body",
        title="Looking for housing",
        body=(
            "Hi, I am an incoming grad moving from CA. Looking for either sublet or lease "
            "takeover or roommates if you're also searching for housing. Anywhere near "
            "East/West Village, Lower Manhattan, Chelsea area."
        ),
        expected_intent="seeker",
    ),
    Case(
        name="seeker_asking_whether_anyone_is_subletting",
        title="looking to rent a room",
        body=(
            "hey I was wondering if anyone is currently subletting a room in their "
            "apartment close to the manhattan campus. I really need a place for the "
            "upcoming semester."
        ),
        expected_intent="seeker",
    ),
    Case(
        name="seeker_wants_to_take_over_a_sublease",
        title="Looking to take over sublease!",
        body=(
            "If anyone is subleasing this summer (ideally jersey city area), I'd be "
            "willing to takeover as I'm starting my internship."
        ),
        expected_intent="seeker",
    ),
    Case(
        name="question_titled_with_weak_offer_word",
        title="Community groups for subleasing",
        body=(
            "Hey y'all I'm interning in new york from september to december and I was "
            "wondering if there were any not super publicized community groups for "
            "subleasing"
        ),
        expected_intent="question",
    ),
    Case(
        name="question_about_dorm_selection",
        title="best upperclassman suites for 2026-27",
        body=(
            "What is the best four-person suite for incoming sophomores? My roommates "
            "and I got one of the earliest selection times."
        ),
        expected_intent="question",
    ),
    Case(
        name="offer_subletting_my_room",
        title="Subletting $800 room- just for girls",
        body=(
            "Subletting my room in the East Village for the fall semester. $800 a month, "
            "furnished, 2 bed 1 bath."
        ),
        expected_intent="offer",
        expected_title="Subletting $800 room- just for girls",
        expected_location="East Village, New York, NY",
    ),
    Case(
        name="offer_neutral_title_decided_by_body",
        title="NYU Fall Sublease",
        body=(
            "I'm studying away in the fall and looking for someone to sublet my room in "
            "a 2 bedroom in the West Village. $1,800/month."
        ),
        expected_intent="offer",
        expected_location="West Village, New York, NY",
    ),
    # "sublease a room" vs "sublease my room" is the whole difference between an
    # intern hunting for a place and an actual listing. Both titles are neutral,
    # so the body has to carry it.
    Case(
        name="seeker_wants_to_sublease_a_room",
        title="NYU Fall Sublease",
        body=(
            "Hi everyone! I'll be interning in NYC this fall and am looking to sublease "
            "a room or apartment from approximately September to December. I'm hoping to "
            "stay near NYU or somewhere with a convenient commute."
        ),
        expected_intent="seeker",
    ),
    Case(
        name="offer_subleasing_my_room",
        title="Place available for sublease Aug 10-30th",
        body=(
            "I'm going on vacation and am looking to sublease my room in Washington "
            "Heights while I'm away. Pm if interested."
        ),
        expected_intent="offer",
        expected_location="Washington Heights, New York, NY",
    ),
    # An incidental "26 min to Manhattan" must not become a Manhattan map pin.
    Case(
        name="incidental_borough_mention_stays_generic",
        title="Subletting my room near Church Av",
        body=(
            "$800 for the room fully furnished, 30 seconds to the F and G Church Av "
            "station, 21 min to NYU Tandon, 26 min to Manhattan, 20 min walk to "
            "Prospect Park."
        ),
        expected_intent="offer",
        expected_location="New York, NY",
    ),
    # Both of these reached the live site. Their bodies are full of housing
    # vocabulary, so only the title gives them away.
    Case(
        name="question_is_this_legal",
        title="Is this subletting situation legal?",
        body=(
            "I'm in a Brooklyn apartment with 2 other roommates. All 3 of us are on "
            "separate subletting leases, and the lessee we rent from doesn't live here. "
            "Is this situation legal? It feels like a workaround to extract more rent."
        ),
        expected_intent="question",
    ),
    Case(
        name="question_lost_my_apartment_is_not_an_offer",
        title="Any Funds for Emergency?",
        body=(
            "Hey guys, I just lost my apartment, having nowhere to go and I don't have "
            "much cash on me. I already depleted my courtesy meals and emergency funds "
            "applications are declined. What other options are there for me?"
        ),
        expected_intent="question",
    ),
    # A real listing that happens to end in a question mark must survive.
    Case(
        name="offer_with_question_mark_title",
        title="Subletting my room in Bushwick, anyone interested?",
        body="$1,500 a month, furnished, available September 1.",
        expected_intent="offer",
    ),
    # Real post: existing roommates with a genuine opening, missed because
    # "looking for A THIRD roommate" has a descriptor the old regex didn't allow.
    Case(
        name="offer_looking_for_a_third_roommate",
        title="Looking for a third roommate in Hamilton Heights! Move-in between 8/01 and 9/01",
        body=(
            "My current roommate and I are looking for a new roommate! Rent is $3700 net "
            "for the unit, with individual shares ranging from 1150-1200 depending on the "
            "room. 2 bed 1 bath, utilities average $150/month."
        ),
        expected_intent="offer",
    ),
    Case(
        name="offer_across_the_river_keeps_nj",
        title="Subletting my room in Jersey City",
        body="Subletting my room from June through August, 10 min on the PATH. $1,400.",
        expected_intent="offer",
        expected_location="Jersey City, NJ",
    ),
    Case(
        name="title_tag_markers_are_stripped",
        title="[Sublet] urgent** Room available in Bushwick",
        body="Subletting my room in Bushwick, $1,500 a month, available now.",
        expected_intent="offer",
        expected_title="Room available in Bushwick",
    ),
]


def entry_for(case: Case) -> RedditFeedEntry:
    return RedditFeedEntry(
        index=0,
        link="https://www.reddit.com/r/nyu/comments/abc123/post/",
        author="someone",
        date="2026-08-01",
        content=case.body,
        image_urls=[],
        title=case.title,
    )


def main() -> None:
    scraper = next(
        source for source in load_sources() if isinstance(source, RedditSearchScraper)
    )
    failures: list[str] = []

    for case in CASES:
        entry = entry_for(case)
        text = scraper._analysis_text(entry)
        intent = scraper._entry_intent(entry, text)
        if intent != case.expected_intent:
            failures.append(f"{case.name}: intent {intent!r} != {case.expected_intent!r}")

        location = scraper._extract_location(text)
        if case.expected_location is not None and location != case.expected_location:
            failures.append(f"{case.name}: location {location!r} != {case.expected_location!r}")

        title = scraper._entry_title(entry, scraper._extract_price(text), location)
        if case.expected_title is not None and title != case.expected_title:
            failures.append(f"{case.name}: title {title!r} != {case.expected_title!r}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        raise SystemExit(1)

    print(f"PASS {len(CASES)} Reddit search edge cases")


if __name__ == "__main__":
    main()
