import { useMemo, useState, type CSSProperties } from 'react';
import type { Listing } from '../types/listing';
import { isNyu } from '../utils/nyu';

// Resolve the hero photo if it has been added to src/assets. Using import.meta.glob
// (instead of a static import) means the app still builds when the file is absent,
// and the photo appears automatically once it is dropped in. Drop a file named
// hero-skyline.{jpg,jpeg,png,webp} into src/assets/ to set the hero background.
const heroImages = import.meta.glob('../assets/hero-skyline.{jpg,jpeg,png,webp}', {
  eager: true,
  query: '?url',
  import: 'default',
});
const heroUrl = Object.values(heroImages)[0] as string | undefined;

interface HomeProps {
  listings: Listing[];
  onBrowse: () => void;
}

function Home({ listings, onBrowse }: HomeProps) {
  const [showListModal, setShowListModal] = useState(false);
  const heroStyle = heroUrl
    ? ({ '--hero-image': `url(${heroUrl})` } as CSSProperties)
    : undefined;

  const stats = useMemo(() => {
    const sources = new Set(listings.map((listing) => listing.platform));
    const verified = listings.filter((listing) => listing.sourceVettedUsers).length;
    const nyu = listings.filter(isNyu).length;
    return {
      total: listings.length,
      sources: sources.size,
      verified,
      nyu,
    };
  }, [listings]);

  return (
    <main className="home">
      <section className={`hero ${heroUrl ? 'hero-photo' : ''}`} style={heroStyle}>
        <p className="hero-eyebrow">For the NYU community</p>
        <h1 className="hero-title">Every NYC sublet, in one place.</h1>
        <p className="hero-mission">
          1StopSublet gathers short-term sublets from across the web and ranks them for
          NYU students - so you can find a safe, simple place to live without checking
          ten different sites.
        </p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={onBrowse}>
            Find a Sublet
          </button>
          <button className="btn btn-secondary" onClick={() => setShowListModal(true)}>
            List Your Sublet
          </button>
        </div>

        <dl className="hero-stats">
          <div className="stat">
            <dt>{stats.total}</dt>
            <dd>live sublets</dd>
          </div>
          <div className="stat">
            <dt>{stats.sources}</dt>
            <dd>sources, one feed</dd>
          </div>
          <div className="stat">
            <dt>{stats.nyu}</dt>
            <dd>near NYU</dd>
          </div>
          <div className="stat">
            <dt>{stats.verified}</dt>
            <dd>verified-student listings</dd>
          </div>
        </dl>
      </section>

      <section className="home-section">
        <h2 className="home-section-title">How it works</h2>
        <div className="card-row">
          <article className="info-card">
            <h3>We gather</h3>
            <p>
              We pull active sublets from verified-student platforms and community boards
              and standardize them into one consistent, scannable feed.
            </p>
          </article>
          <article className="info-card">
            <h3>We rank for NYU</h3>
            <p>
              Listings near Washington Square or Tandon and from the NYU community rise
              to the top, so the most relevant options come first.
            </p>
          </article>
          <article className="info-card">
            <h3>We flag trust</h3>
            <p>
              Every listing shows where it came from and whether the source verifies its
              users, so you always know what you are looking at.
            </p>
          </article>
        </div>
      </section>

      <section className="home-section home-section-dark trust-section">
        <h2 className="home-section-title">Know who you are renting from</h2>
        <p className="home-section-lead">
          Not every listing is equal. We label each one by how much its source vets the
          people posting it.
        </p>
        <div className="card-row">
          <article className="info-card">
            <span className="trust-badge trust-verified">Verified student</span>
            <p>
              From platforms that require a student account to post, like Subletr. The
              lister is a confirmed student.
            </p>
          </article>
          <article className="info-card">
            <span className="trust-badge trust-official">Official portal</span>
            <p>
              NYU&rsquo;s own off-campus housing portal sits behind a NetID login, so we
              can&rsquo;t mirror it here.{' '}
              <a href="https://offcampushousing.nyu.edu" target="_blank" rel="noreferrer">
                Search it directly
              </a>{' '}
              with your NYU account - it is worth checking alongside this feed.
            </p>
          </article>
          <article className="info-card">
            <span className="trust-badge trust-unverified">Community post</span>
            <p>
              From open boards like Reddit. Useful leads, but the poster is not verified -
              meet safely and confirm details.
            </p>
          </article>
        </div>
      </section>

      <section className="home-cta">
        <h2>Ready to find your next place?</h2>
        <button className="btn btn-primary" onClick={onBrowse}>
          Browse {stats.total} sublets
        </button>
      </section>

      {showListModal && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="list-modal-title"
          onClick={() => setShowListModal(false)}
        >
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <button
              className="modal-close"
              onClick={() => setShowListModal(false)}
              aria-label="Close"
            >
              &times;
            </button>
            <h2 id="list-modal-title">List your sublet</h2>
            <p>
              Posting directly on 1StopSublet is coming soon. For now, post on one of our
              verified-student partners and your listing will show up here automatically:
            </p>
            <div className="modal-actions">
              <a
                className="btn btn-primary"
                href="https://www.subletr.com"
                target="_blank"
                rel="noreferrer"
              >
                Post on Subletr
              </a>
              <a
                className="btn btn-secondary"
                href="https://www.reddit.com/r/nyu/"
                target="_blank"
                rel="noreferrer"
              >
                Post on r/nyu
              </a>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default Home;
