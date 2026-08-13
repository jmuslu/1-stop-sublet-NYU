import type { Listing } from '../types/listing';

// Signals that a listing is from / for the NYU community. Includes the schools
// students name instead of "NYU" (Tisch, Stern, Gallatin, Tandon, ...).
const NYU_RE =
  /\bnyu\b|new york university|violets|bobcats|tisch|stern|gallatin|steinhardt|tandon|courant|\bwagner\b|silver school|liberal studies|\bcas\b|\bsps\b/i;
// Neighborhoods on or next to NYU's two campuses - relevant even when the poster
// is elsewhere. Washington Square is the core; Tandon sits in downtown Brooklyn.
const NEAR_NYU_RE =
  /washington square|greenwich village|west village|east village|\bnoho\b|\bsoho\b|nolita|lower east side|\bles\b|alphabet city|union square|gramercy|\bchelsea\b|\bflatiron\b|\bbowery\b|astor place|\bfidi\b|financial district|\btribeca\b|chinatown|two bridges|kips bay|murray hill|downtown brooklyn|\bdumbo\b|brooklyn heights|metrotech|\bcobble hill\b|boerum hill/i;
// Other NYC-area schools we want ranked below NYU content.
const OTHER_SCHOOL_RE =
  /\bcolumbia\b|barnard|fordham|the new school|parsons|\bpace\b|baruch|hunter college|\bcuny\b|city college|st\.? john's|pratt institute|\bsva\b|school of visual arts|juilliard|cooper union|yeshiva|\bnjit\b|stevens institute|touro|\bfit\b|fashion institute/i;

function searchableText(listing: Listing): string {
  return [
    listing.title,
    listing.description,
    listing.location,
    listing.school,
    listing.sourceSubreddit,
    listing.sourceThreadTitle,
    ...(listing.amenities ?? []),
  ]
    .filter(Boolean)
    .join(' ');
}

/** True when the listing is explicitly tied to NYU. */
export function isNyu(listing: Listing): boolean {
  return NYU_RE.test(searchableText(listing));
}

/**
 * Relevance score for ordering the feed: NYU listings/asks float to the top,
 * listings near either campus sit in the middle, and listings tied to other NYC
 * schools sink to the bottom. Higher is more relevant.
 */
export function nyuScore(listing: Listing): number {
  const text = searchableText(listing);
  let score = 0;
  if (NYU_RE.test(text)) score += 100;
  if (NEAR_NYU_RE.test(text)) score += 40;
  if (OTHER_SCHOOL_RE.test(text) && !NYU_RE.test(text)) score -= 60;
  return score;
}
