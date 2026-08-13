# Scraper Sources

Each source gets one config file here and, when needed, one Python scraper class.

The scraper output is static: `npm run scrape` writes `src/data/generatedListings.json`, and the Vite app imports that file at build time. This keeps 1StopSublet deployable on GitHub Pages without a backend.

To add a real source:

1. Create a scraper class in this folder that extends `ListingScraper`.
2. Add that class to `SCRAPER_TYPES` in `../registry.py`.
3. Add a JSON config in this folder with its source-specific knobs.
4. Normalize every item to `NormalizedListing`, especially `sourceUrl`, `dateListed`, `price`, `location`, `amenities`, and `sourceVettedUsers`.

Use one source per file. That keeps website-specific parsing, rate limits, selectors, and cleanup rules easy to swap without touching the React app.

## Current Sources

- `reddit_nyu_posts.json` is the primary source. It reads Reddit's public Atom feed for a **subreddit search** of r/nyu (`/r/nyu/search.rss`) rather than a single thread, because r/nyu students post sublets as ordinary threads. Reddit's JSON API is often blocked for unauthenticated requests, so the scraper intentionally uses RSS/Atom and keeps previous generated data for that source if Reddit rate-limits a scheduled build. Listers are unverified (`vetted_users: false`).
- `reddit_nyu_megathread.json` is the r/nyu housing megathread, kept at `enabled: false`. It is the direct analogue of the Boston version's r/NEU source, but the thread has had no comments since March 2024. Flip `enabled` back to `true` if the mods revive it.
- `facebook_nyu_group.json` first attempts to read the public mobile Facebook group preview without an account. If Facebook returns a login page or too few public posts, `scrapers/manual/facebook_export_browser_console.js` can still be run in a logged-in browser to download visible posts as `facebook_group_posts.json`, then the scraper normalizes those posts into the same listing contract.
- `subletr.json` parses Subletr's (https://www.subletr.com) server-rendered `/listings` index; no API key or sign-in is needed to browse. Posting requires a verified student account, so `vetted_users: true`. Its `states` and `cities` lists are what keep out-of-area campuses out of the feed — Subletr is nationwide and currently Boston-heavy, so NYC inventory may be empty on any given run.

## Config knobs worth knowing

- `city_suffix` is appended to a matched `location_terms` entry, e.g. `East Village` becomes `East Village, New York, NY`.
- `location_suffix_overrides` handles neighborhoods outside the default city/state, so `Jersey City` becomes `Jersey City, NJ` and not `Jersey City, New York, NY`.
- `thread_url` is optional and only meaningful for `reddit_thread`; a search feed has no originating post to skip.

Any neighborhood added to `location_terms` should also get coordinates in `src/utils/geo.ts`, or it will fall into the generic "NYC area" map pin.

## Removed Boston sources

`sblt.json` and `neu_aptsearch.json` were dropped in this port. SBLT is Boston-only, and NYU's off-campus housing portal requires a NetID login where Northeastern's aptsearch was public. See the top-level README for details.
