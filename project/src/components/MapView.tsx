import { useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Listing } from '../types/listing';
import { groupByNeighborhood, CAMPUSES, MAP_CENTER, TRANSIT_STOPS } from '../utils/geo';

interface MapViewProps {
  listings: Listing[];
}

function priceLabel(listing: Listing): string {
  return listing.price == null ? 'Ask' : `$${listing.price.toLocaleString('en-US')}`;
}

/** Neighborhood pin: brand-red pill showing the area name and how many sublets are there. */
function neighborhoodIcon(label: string, count: number): L.DivIcon {
  return L.divIcon({
    className: '',
    html: `<span class="map-pin map-pin-nu">${label} · ${count}</span>`,
    iconSize: [0, 0],
    iconAnchor: [0, 0],
  });
}

const campusIcon = L.divIcon({
  className: '',
  html: '<span class="map-campus">NYU</span>',
  iconSize: [0, 0],
  iconAnchor: [0, 0],
});

// NYC subway roundel rather than the MBTA "T".
const transitIcon = L.divIcon({
  className: '',
  html: '<span class="map-transit">M</span>',
  iconSize: [0, 0],
  iconAnchor: [0, 0],
});

function MapView({ listings }: MapViewProps) {
  const groups = useMemo(() => groupByNeighborhood(listings), [listings]);

  return (
    <div className="map-wrap">
      <div className="map-notice" role="note">
        <strong>Example view.</strong> Sublets are grouped by neighborhood and placed
        approximately - we can&rsquo;t verify exact listing locations yet. Open a listing for its
        real address.
      </div>

      <MapContainer
        center={MAP_CENTER}
        zoom={12}
        scrollWheelZoom={false}
        className="map-container"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {CAMPUSES.map((campus) => (
          <Marker key={campus.name} position={campus.coords} icon={campusIcon}>
            <Popup>
              <strong>{campus.name}</strong>
            </Popup>
          </Marker>
        ))}

        {TRANSIT_STOPS.map((stop) => (
          <Marker key={stop.name} position={stop.coords} icon={transitIcon}>
            <Popup>
              <strong>{stop.name}</strong>
              <br />
              {stop.line}
            </Popup>
          </Marker>
        ))}

        {groups.map((group) => (
          <Marker
            key={group.key}
            position={group.coords}
            icon={neighborhoodIcon(group.label, group.listings.length)}
          >
            <Popup>
              <div className="map-popup">
                <strong className="map-popup-title">
                  {group.label} · {group.listings.length} sublet
                  {group.listings.length === 1 ? '' : 's'}
                </strong>
                <ul className="map-popup-list">
                  {group.listings.slice(0, 4).map((listing) => (
                    <li key={listing.id}>
                      <a href={listing.sourceUrl} target="_blank" rel="noreferrer">
                        {listing.title}
                      </a>
                      <span className="map-popup-meta">
                        {priceLabel(listing)}
                        {listing.price != null && '/mo'} ·{' '}
                        {listing.bedrooms === 0 ? 'Studio' : `${listing.bedrooms} BR`} ·{' '}
                        {listing.platform}
                      </span>
                    </li>
                  ))}
                </ul>
                {group.listings.length > 4 && (
                  <span className="map-popup-meta">
                    +{group.listings.length - 4} more in the list view
                  </span>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      <div className="map-legend" aria-hidden="true">
        <span>
          <i className="legend-dot legend-campus">NYU</i> Campus
        </span>
        <span>
          <i className="legend-dot legend-transit">M</i> Subway
        </span>
        <span>
          <i className="legend-dot legend-nu" /> Sublets by neighborhood
        </span>
      </div>
    </div>
  );
}

export default MapView;
