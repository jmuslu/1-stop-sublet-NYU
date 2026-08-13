from __future__ import annotations

import re

from scrapers.sources.reddit import RedditFeedEntry, RedditThreadScraper


class RedditSearchScraper(RedditThreadScraper):
    """Standalone sublet posts from a subreddit's public search feed.

    r/NEU funnels housing into a single pinned megathread, so the thread scraper
    reads that thread's comment feed. r/nyu works the other way round: its housing
    megathread has been dormant since early 2024 and students post sublets as
    ordinary threads instead. Reddit exposes subreddit search as Atom at
    ``/r/<sub>/search.rss``, which has the same entry shape as a comment feed, so
    this only has to change two things:

    - the post title is folded into the text the extractors and the intent
      classifier read, since for a standalone post that is where "subletting my
      room" vs "looking for a room" actually lives, and
    - the post's own title is used as the listing title instead of a sentence
      pulled out of the body.
    """

    def _entry_intent(self, entry: RedditFeedEntry, text: str) -> str:
        """Classify on the title first, falling back to the whole post.

        A standalone post states its intent in the title, but the body of a
        *seeker* post is full of offer vocabulary - "is anyone subletting a
        room", "I'd take over a lease". Reading the body first turns "Looking
        for housing" into an offer, so a title that positively matches wins and
        the body only decides when the title says nothing either way.
        """
        title_intent = self._title_intent(self._clean_title(entry.title))
        if title_intent is not None:
            return title_intent
        return self._classify_intent(text, has_images=bool(entry.image_urls))

    def _title_intent(self, title: str) -> str | None:
        """Intent from the title alone, or None when the title is uninformative.

        Deliberately not ``_classify_intent_with_rules``: that falls back to
        "seeker" when nothing matches, which would sink every offer with a
        neutral title.

        Only ``strong_offer_terms`` can settle an offer here. The weak
        ``offer_terms`` are single words like "subleasing", which show up just as
        readily in a title that is asking for one ("Community groups for
        subleasing") - those fall through to the body, which has the context.
        """
        if not title:
            return None
        lowered = title.lower().replace("’", "'")
        if self._contains_config_term(lowered, "strong_offer_terms"):
            return "offer"
        if self._contains_config_term(lowered, "exclude_terms"):
            return "seeker"
        if self._contains_config_term(lowered, "seeker_terms"):
            return "seeker"
        if self._contains_config_term(lowered, "question_terms"):
            return "question"
        return None

    def _analysis_text(self, entry: RedditFeedEntry) -> str:
        if not entry.title:
            return entry.content
        return f"{entry.title}. {entry.content}"

    def _entry_title(self, entry: RedditFeedEntry, price: int | None, location: str) -> str:
        title = self._clean_title(entry.title)
        if title:
            return self._trim(title, 80)
        return super()._entry_title(entry, price, location)

    def _clean_title(self, title: str) -> str:
        """Strip the leading tag markers students put on r/nyu post titles."""
        cleaned = re.sub(r"^\s*(?:\[[^\]]*\]|\([^)]*\))\s*", "", title)
        cleaned = re.sub(r"^\s*(?:urgent\**|asap)\s*[:\-—]*\s*", "", cleaned, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", cleaned).strip()
