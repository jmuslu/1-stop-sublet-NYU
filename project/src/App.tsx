import { useState, useMemo, useEffect } from 'react';
import type { Listing, ListingPlatform, SortOption } from './types/listing';
import generatedListings from './data/generatedListings.json';
import Header, { type View } from './components/Header';
import Home from './components/Home';
import FilterBar from './components/FilterBar';
import SearchBar from './components/SearchBar';
import ListingGrid from './components/ListingGrid';
import MapView from './components/MapView';
import { nyuScore } from './utils/nyu';
import { matchesSearch } from './utils/search';
import { locationFilterValue } from './utils/geo';
import './App.css';

type ResultsView = 'grid' | 'map';

function App() {
  const [view, setView] = useState<View>('home');
  const [selectedPlatform, setSelectedPlatform] = useState<ListingPlatform | 'all'>('all');
  const [selectedLocation, setSelectedLocation] = useState('all');
  const [sortBy, setSortBy] = useState<SortOption>('date-desc');
  const [searchQuery, setSearchQuery] = useState('');
  const [resultsView, setResultsView] = useState<ResultsView>('grid');
  const listings = generatedListings as Listing[];

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [view]);

  const locations = useMemo(() => {
    const uniqueLocations = new Set(listings.map((listing) => locationFilterValue(listing.location)));
    return Array.from(uniqueLocations).sort();
  }, [listings]);

  const platforms = useMemo(() => {
    const uniquePlatforms = new Set(listings.map((l) => l.platform));
    return Array.from(uniquePlatforms).sort();
  }, [listings]);

  const filteredAndSortedListings = useMemo(() => {
    let result = [...listings];

    if (selectedPlatform !== 'all') {
      result = result.filter((listing) => listing.platform === selectedPlatform);
    }

    if (selectedLocation !== 'all') {
      result = result.filter((listing) => locationFilterValue(listing.location) === selectedLocation);
    }

    if (searchQuery.trim()) {
      result = result.filter((listing) => matchesSearch(listing, searchQuery));
    }

    result.sort((a, b) => {
      // The chosen sort is what the dropdown says it is - there is no
      // "Relevance" option, so a listing 100 spots newer must never rank
      // below an older one just because it scores higher on nyuScore.
      // Relevance only breaks ties within the primary key (same day, or both
      // priceless), which is also where it is most useful: many listings
      // land on the same dateListed, and NYU-relevant ones should float to
      // the top of that group rather than sort arbitrarily.
      const primary = (() => {
        switch (sortBy) {
          case 'date-desc':
            return new Date(b.dateListed).getTime() - new Date(a.dateListed).getTime();
          case 'date-asc':
            return new Date(a.dateListed).getTime() - new Date(b.dateListed).getTime();
          case 'price-desc':
            return (b.price ?? -1) - (a.price ?? -1);
          case 'price-asc':
            return (a.price ?? Number.MAX_SAFE_INTEGER) - (b.price ?? Number.MAX_SAFE_INTEGER);
          default:
            return 0;
        }
      })();
      if (primary !== 0) {
        return primary;
      }
      return nyuScore(b) - nyuScore(a);
    });

    return result;
  }, [listings, selectedPlatform, selectedLocation, searchQuery, sortBy]);

  return (
    <div className="app">
      <Header view={view} onNavigate={setView} />
      {view === 'home' ? (
        <Home listings={listings} onBrowse={() => setView('browse')} />
      ) : (
        <main className="main-content">
          <SearchBar value={searchQuery} onChange={setSearchQuery} />
          <FilterBar
            selectedPlatform={selectedPlatform}
            onPlatformChange={setSelectedPlatform}
            platforms={platforms}
            selectedLocation={selectedLocation}
            onLocationChange={setSelectedLocation}
            locations={locations}
            sortBy={sortBy}
            onSortChange={setSortBy}
          />
          {selectedPlatform === 'Facebook' && (
            <p className="source-note">
              Facebook only shows a limited public preview here. Sign in to Facebook to view more posts from the group.
            </p>
          )}
          <div className="results-bar">
            <div className="results-count">
              {filteredAndSortedListings.length} listings found
            </div>
            <div className="view-toggle" role="group" aria-label="Results view">
              <button
                type="button"
                className={`view-toggle-btn ${resultsView === 'grid' ? 'active' : ''}`}
                onClick={() => setResultsView('grid')}
                aria-pressed={resultsView === 'grid'}
              >
                Grid
              </button>
              <button
                type="button"
                className={`view-toggle-btn ${resultsView === 'map' ? 'active' : ''}`}
                onClick={() => setResultsView('map')}
                aria-pressed={resultsView === 'map'}
              >
                Map
              </button>
            </div>
          </div>
          {resultsView === 'grid' ? (
            <ListingGrid listings={filteredAndSortedListings} />
          ) : (
            <MapView listings={filteredAndSortedListings} />
          )}
        </main>
      )}
      <footer className="footer">
        <p>1StopSublet - your centralized sublet marketplace for the NYU community</p>
      </footer>
    </div>
  );
}

export default App;
