import type { Listing } from '../types/listing';

export type LatLng = [number, number];

/**
 * The listing data has no real coordinates - only neighborhood strings (e.g.
 * "East Village, New York, NY"). We can't yet verify exact addresses, so the map
 * is an illustrative example: listings are grouped by neighborhood and shown as
 * a single pin at the neighborhood's approximate centroid. Nothing here claims
 * to be an exact location.
 *
 * Each neighborhood is listed twice - once as "X, NY" (what Subletr emits) and
 * once as "X, New York, NY" (what the Reddit/Facebook scrapers emit) - so both
 * source shapes land on the same pin.
 */
const NEIGHBORHOOD_COORDS: Record<string, LatLng> = {
  // Manhattan - around Washington Square
  'Greenwich Village, NY': [40.7336, -74.0027],
  'Greenwich Village, New York, NY': [40.7336, -74.0027],
  'West Village, NY': [40.7358, -74.0036],
  'West Village, New York, NY': [40.7358, -74.0036],
  'East Village, NY': [40.7265, -73.9815],
  'East Village, New York, NY': [40.7265, -73.9815],
  'NoHo, NY': [40.7284, -73.9937],
  'NoHo, New York, NY': [40.7284, -73.9937],
  'SoHo, NY': [40.7233, -74.003],
  'SoHo, New York, NY': [40.7233, -74.003],
  'Nolita, NY': [40.7222, -73.9955],
  'Nolita, New York, NY': [40.7222, -73.9955],
  'Lower East Side, NY': [40.715, -73.9843],
  'Lower East Side, New York, NY': [40.715, -73.9843],
  'Chinatown, NY': [40.7158, -73.997],
  'Chinatown, New York, NY': [40.7158, -73.997],
  'Tribeca, NY': [40.7163, -74.0086],
  'Tribeca, New York, NY': [40.7163, -74.0086],
  'Financial District, NY': [40.7075, -74.0113],
  'Financial District, New York, NY': [40.7075, -74.0113],
  'Union Square, NY': [40.7359, -73.9911],
  'Union Square, New York, NY': [40.7359, -73.9911],
  'Flatiron, NY': [40.7401, -73.9903],
  'Flatiron, New York, NY': [40.7401, -73.9903],
  'Gramercy, NY': [40.7368, -73.9845],
  'Gramercy, New York, NY': [40.7368, -73.9845],
  'Kips Bay, NY': [40.7424, -73.98],
  'Kips Bay, New York, NY': [40.7424, -73.98],
  'Murray Hill, NY': [40.7479, -73.9756],
  'Murray Hill, New York, NY': [40.7479, -73.9756],
  'Chelsea, NY': [40.7465, -74.0014],
  'Chelsea, New York, NY': [40.7465, -74.0014],
  "Hell's Kitchen, NY": [40.7638, -73.9918],
  "Hell's Kitchen, New York, NY": [40.7638, -73.9918],
  'Upper East Side, NY': [40.7736, -73.9566],
  'Upper East Side, New York, NY': [40.7736, -73.9566],
  'Upper West Side, NY': [40.787, -73.9754],
  'Upper West Side, New York, NY': [40.787, -73.9754],
  'Morningside Heights, NY': [40.8075, -73.9626],
  'Morningside Heights, New York, NY': [40.8075, -73.9626],
  'Harlem, NY': [40.8116, -73.9465],
  'Harlem, New York, NY': [40.8116, -73.9465],
  'East Harlem, NY': [40.7947, -73.9425],
  'East Harlem, New York, NY': [40.7947, -73.9425],
  'Washington Heights, NY': [40.8417, -73.9394],
  'Washington Heights, New York, NY': [40.8417, -73.9394],
  'Hamilton Heights, NY': [40.8252, -73.9496],
  'Hamilton Heights, New York, NY': [40.8252, -73.9496],
  'Inwood, NY': [40.8677, -73.9212],
  'Inwood, New York, NY': [40.8677, -73.9212],
  'Roosevelt Island, NY': [40.7615, -73.95],
  'Roosevelt Island, New York, NY': [40.7615, -73.95],
  'Manhattan, NY': [40.7549, -73.984],
  'Manhattan, New York, NY': [40.7549, -73.984],

  // Brooklyn - around Tandon / downtown Brooklyn
  'Downtown Brooklyn, NY': [40.6928, -73.986],
  'Downtown Brooklyn, New York, NY': [40.6928, -73.986],
  'DUMBO, NY': [40.7033, -73.9881],
  'DUMBO, New York, NY': [40.7033, -73.9881],
  'Brooklyn Heights, NY': [40.6962, -73.9932],
  'Brooklyn Heights, New York, NY': [40.6962, -73.9932],
  'Fort Greene, NY': [40.6892, -73.974],
  'Fort Greene, New York, NY': [40.6892, -73.974],
  'Williamsburg, NY': [40.7081, -73.9571],
  'Williamsburg, New York, NY': [40.7081, -73.9571],
  'Greenpoint, NY': [40.7304, -73.954],
  'Greenpoint, New York, NY': [40.7304, -73.954],
  'Bushwick, NY': [40.6944, -73.9213],
  'Bushwick, New York, NY': [40.6944, -73.9213],
  'Bedford-Stuyvesant, NY': [40.6872, -73.9418],
  'Bedford-Stuyvesant, New York, NY': [40.6872, -73.9418],
  'Prospect Heights, NY': [40.6774, -73.9668],
  'Prospect Heights, New York, NY': [40.6774, -73.9668],
  'Crown Heights, NY': [40.6694, -73.9422],
  'Crown Heights, New York, NY': [40.6694, -73.9422],
  'Park Slope, NY': [40.671, -73.9814],
  'Park Slope, New York, NY': [40.671, -73.9814],
  'Carroll Gardens, NY': [40.6795, -73.9991],
  'Carroll Gardens, New York, NY': [40.6795, -73.9991],
  'Ridgewood, NY': [40.7043, -73.9018],
  'Ridgewood, New York, NY': [40.7043, -73.9018],
  'Clinton Hill, NY': [40.6896, -73.9661],
  'Clinton Hill, New York, NY': [40.6896, -73.9661],
  'Boerum Hill, NY': [40.6852, -73.9838],
  'Boerum Hill, New York, NY': [40.6852, -73.9838],
  'Gowanus, NY': [40.6736, -73.9896],
  'Gowanus, New York, NY': [40.6736, -73.9896],
  'Red Hook, NY': [40.6751, -74.0093],
  'Red Hook, New York, NY': [40.6751, -74.0093],
  'Windsor Terrace, NY': [40.6553, -73.9752],
  'Windsor Terrace, New York, NY': [40.6553, -73.9752],
  'Sunset Park, NY': [40.6455, -74.0122],
  'Sunset Park, New York, NY': [40.6455, -74.0122],
  'Prospect Lefferts Gardens, NY': [40.6592, -73.9557],
  'Prospect Lefferts Gardens, New York, NY': [40.6592, -73.9557],
  'Ditmas Park, NY': [40.6395, -73.9645],
  'Ditmas Park, New York, NY': [40.6395, -73.9645],
  'Flatbush, NY': [40.6409, -73.9624],
  'Flatbush, New York, NY': [40.6409, -73.9624],
  'Bay Ridge, NY': [40.6264, -74.0299],
  'Bay Ridge, New York, NY': [40.6264, -74.0299],
  'Brooklyn, NY': [40.6782, -73.9442],
  'Brooklyn, New York, NY': [40.6782, -73.9442],

  // Queens + across the river
  'Long Island City, NY': [40.7447, -73.9485],
  'Long Island City, New York, NY': [40.7447, -73.9485],
  'Astoria, NY': [40.7644, -73.9235],
  'Astoria, New York, NY': [40.7644, -73.9235],
  'Sunnyside, NY': [40.7433, -73.9196],
  'Sunnyside, New York, NY': [40.7433, -73.9196],
  'Queens, NY': [40.7282, -73.7949],
  'Queens, New York, NY': [40.7282, -73.7949],
  'Jersey City, NJ': [40.7178, -74.0431],
  'Hoboken, NJ': [40.744, -74.0324],
  'Newark, NJ': [40.7357, -74.1724],
};

// Listings with no specific neighborhood ("New York, NY" or anything unmapped)
// are collected into one "NYC area" pin placed centrally between the campuses.
const GENERIC_KEY = 'NYC area';
// Placed north-east of Washington Square (toward Midtown South) so this large
// catch-all pin doesn't sit on top of the campus markers.
const GENERIC_COORDS: LatLng = [40.7465, -73.9835];

export interface Campus {
  name: string;
  short: string;
  coords: LatLng;
}

/** NYU's two main campuses - the anchor points of the map. */
export const CAMPUSES: Campus[] = [
  { name: 'NYU - Washington Square', short: 'NYU', coords: [40.7295, -73.9965] },
  { name: 'NYU Tandon - Brooklyn', short: 'NYU', coords: [40.6942, -73.9866] },
];

/** Map centers between Washington Square and Tandon so both campuses are visible. */
export const MAP_CENTER: LatLng = [40.7135, -73.9915];

/** Nearby subway stops, so renters can see each area relative to transit. */
export const TRANSIT_STOPS: { name: string; line: string; coords: LatLng }[] = [
  { name: 'W 4 St - Washington Sq', line: 'A/C/E · B/D/F/M', coords: [40.7323, -74.0007] },
  { name: '8 St - NYU', line: 'R/W', coords: [40.7305, -73.9925] },
  { name: 'Astor Pl', line: '6', coords: [40.73, -73.9911] },
  { name: '14 St - Union Sq', line: '4/5/6 · L · N/Q/R/W', coords: [40.735, -73.9903] },
  { name: 'Broadway - Lafayette St', line: 'B/D/F/M', coords: [40.7253, -73.9962] },
  { name: 'Christopher St - Sheridan Sq', line: '1', coords: [40.7337, -74.003] },
  { name: 'Canal St', line: 'J/Z · N/Q/R/W · 6', coords: [40.7188, -74.0001] },
  { name: 'Jay St - MetroTech', line: 'A/C/F · R', coords: [40.6923, -73.9873] },
];

export interface NeighborhoodGroup {
  key: string;
  label: string;
  coords: LatLng;
  listings: Listing[];
}

export function locationFilterValue(location: string): string {
  const normalized = location.trim().replace(/\s+/g, ' ');
  if (normalized === 'New York, NY') {
    return normalized;
  }
  if (normalized.endsWith(', New York, NY')) {
    return normalized.replace(', New York, NY', ', NY');
  }
  return normalized;
}

/**
 * Group listings into neighborhood pins for the example map. Each known
 * neighborhood becomes one pin at its centroid; everything else collapses into
 * a single "NYC area" pin. Returns groups largest-first.
 */
export function groupByNeighborhood(listings: Listing[]): NeighborhoodGroup[] {
  const groups = new Map<string, NeighborhoodGroup>();

  for (const listing of listings) {
    const location = locationFilterValue(listing.location);
    const known = NEIGHBORHOOD_COORDS[location];
    const key = known ? location : GENERIC_KEY;
    const existing = groups.get(key);
    if (existing) {
      existing.listings.push(listing);
    } else {
      groups.set(key, {
        key,
        label: known ? location.split(',')[0].trim() : GENERIC_KEY,
        coords: known ?? GENERIC_COORDS,
        listings: [listing],
      });
    }
  }

  return Array.from(groups.values()).sort((a, b) => b.listings.length - a.listings.length);
}
