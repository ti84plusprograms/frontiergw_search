"use client";

import { useEffect, useState } from "react";

import { Airport, searchAirports } from "@/lib/airportSearch";

export default function Home() {
  return (
    <main>
      <h1>Frontier GoWild Destination Explorer</h1>
      <p>Find where you can fly today.</p>
      <AirportCombobox />
    </main>
  );
}

function AirportCombobox() {
  const [query, setQuery] = useState("");
  const [airports, setAirports] = useState<Airport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!query.trim()) {
      setAirports([]);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    searchAirports(query)
      .then((items) => {
        if (!cancelled) setAirports(items);
      })
      .catch(() => {
        if (!cancelled) setError("Airport search is unavailable. Try again.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [query]);

  return (
    <section aria-labelledby="origin-label">
      <label id="origin-label" htmlFor="origin-airport">
        Departure airport
      </label>
      <input
        id="origin-airport"
        role="combobox"
        aria-autocomplete="list"
        aria-controls="airport-results"
        aria-expanded={airports.length > 0}
        autoComplete="off"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search by city or airport code"
      />
      {loading && <p role="status">Searching airports…</p>}
      {error && <p role="alert">{error}</p>}
      {airports.length > 0 && (
        <ul id="airport-results" role="listbox" aria-label="Airport results">
          {airports.map((airport) => (
            <li key={airport.code} role="option" aria-selected="false">
              <button type="button" onClick={() => setQuery(`${airport.code} — ${airport.city}`)}>
                {airport.code} — {airport.city}, {airport.state_or_region ?? airport.country_code}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
