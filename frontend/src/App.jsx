import { useEffect, useMemo, useState } from "react";
import { getDestinations, getPlaces } from "./api/client.js";

function formatCategory(category) {
  return category || "Uncategorized";
}

function PlaceCard({ place }) {
  return (
    <article className="place-card">
      <div className="place-card__topline">
        <span className="category-tag">{formatCategory(place.category)}</span>
        {place.url && (
          <a className="place-link" href={place.url} target="_blank" rel="noreferrer">
            Open <span aria-hidden="true">↗</span>
          </a>
        )}
      </div>
      <h3>{place.name}</h3>
      {place.address && <p className="place-address">{place.address}</p>}
      {place.note && <p className="place-note">{place.note}</p>}
      {(place.latitude != null || place.longitude != null) && (
        <p className="place-coordinates">
          {[place.latitude, place.longitude].filter((value) => value != null).join(", ")}
        </p>
      )}
    </article>
  );
}

export default function App() {
  const [destinations, setDestinations] = useState([]);
  const [selectedDestinationId, setSelectedDestinationId] = useState("");
  const [places, setPlaces] = useState([]);
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [destinationsLoading, setDestinationsLoading] = useState(true);
  const [placesLoading, setPlacesLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getDestinations()
      .then((items) => {
        if (!cancelled) {
          setDestinations(items);
          setSelectedDestinationId(items[0] ? String(items[0].id) : "");
        }
      })
      .catch((requestError) => {
        if (!cancelled) setError(`Could not load destinations: ${requestError.message}`);
      })
      .finally(() => {
        if (!cancelled) setDestinationsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedDestinationId) {
      setPlaces([]);
      return undefined;
    }
    let cancelled = false;
    setPlacesLoading(true);
    setError("");
    setCategoryFilter("All");
    getPlaces(selectedDestinationId)
      .then((items) => {
        if (!cancelled) setPlaces(items);
      })
      .catch((requestError) => {
        if (!cancelled) setError(`Could not load places: ${requestError.message}`);
      })
      .finally(() => {
        if (!cancelled) setPlacesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedDestinationId]);

  const selectedDestination = destinations.find(
    (destination) => String(destination.id) === selectedDestinationId,
  );
  const categories = useMemo(
    () => [...new Set(places.map((place) => formatCategory(place.category)))].sort(),
    [places],
  );
  const visiblePlaces =
    categoryFilter === "All"
      ? places
      : places.filter((place) => formatCategory(place.category) === categoryFilter);

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Trip Organizer home">
          <span className="brand-mark" aria-hidden="true">T</span>
          <span>Trip Organizer</span>
        </a>
        <span className="topbar-caption">YOUR SAVED PLACES, IN ONE VIEW</span>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <div className="sidebar-heading">
            <span className="eyebrow">YOUR LIBRARY</span>
            <h2>Destinations</h2>
          </div>
          {destinationsLoading ? (
            <p className="muted">Loading destinations…</p>
          ) : destinations.length ? (
            <nav className="destination-list" aria-label="Destinations">
              {destinations.map((destination) => (
                <button
                  className={`destination-button ${String(destination.id) === selectedDestinationId ? "is-selected" : ""}`}
                  key={destination.id}
                  onClick={() => setSelectedDestinationId(String(destination.id))}
                  type="button"
                >
                  <span className="destination-dot" aria-hidden="true" />
                  <span>{destination.name}</span>
                  <span className="destination-arrow" aria-hidden="true">›</span>
                </button>
              ))}
            </nav>
          ) : (
            <p className="muted sidebar-empty">No destinations imported yet.</p>
          )}
          <div className="sidebar-footer">
            <span className="status-dot" /> Local collection
          </div>
        </aside>

        <main className="content">
          <section className="destination-header">
            <div>
              <span className="eyebrow">EXPLORE YOUR COLLECTION</span>
              <h1>{selectedDestination?.name || "Your next adventure"}</h1>
              <p className="destination-summary">
                {selectedDestination
                  ? "A little inspiration for wherever the day takes you."
                  : "Import your saved places to get started."}
              </p>
            </div>
            {selectedDestination && (
              <div className="place-count">
                <strong>{places.length}</strong>
                <span>{places.length === 1 ? "PLACE" : "PLACES"}</span>
              </div>
            )}
          </section>

          {error && <div className="notice notice--error" role="alert">{error}</div>}

          {selectedDestination && (
            <section className="places-section" aria-label="Places">
              <div className="section-heading">
                <div>
                  <h2>Saved places</h2>
                  <p>Browse by the kind of stop you have in mind.</p>
                </div>
              </div>
              {!!categories.length && (
                <div className="category-filters" aria-label="Filter by category">
                  {["All", ...categories].map((category) => (
                    <button
                      className={`filter-chip ${categoryFilter === category ? "is-active" : ""}`}
                      key={category}
                      onClick={() => setCategoryFilter(category)}
                      type="button"
                    >
                      {category}
                    </button>
                  ))}
                </div>
              )}

              {placesLoading ? (
                <div className="empty-state">Loading saved places…</div>
              ) : visiblePlaces.length ? (
                <div className="place-grid">
                  {visiblePlaces.map((place) => <PlaceCard key={place.id} place={place} />)}
                </div>
              ) : (
                <div className="empty-state">
                  {places.length
                    ? `No places in ${categoryFilter}.`
                    : "No places found for this destination."}
                </div>
              )}
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
