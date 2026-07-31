import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { searchAirports } from "./airportSearch.ts";

describe("searchAirports", () => {
  it("requests the API and returns airport results", async () => {
    const response = {
      ok: true,
      json: async () => ({ items: [{ code: "ATL", city: "Atlanta" }] }),
    } as Response;
    let requestedUrl = "";

    const airports = await searchAirports(" atl ", async (input) => {
      requestedUrl = String(input);
      return response;
    });

    assert.match(requestedUrl, /\/airports\?query=atl&limit=10/);
    assert.deepEqual(airports, [{ code: "ATL", city: "Atlanta" }]);
  });

  it("does not call the API for an empty query", async () => {
    let called = false;
    const airports = await searchAirports("  ", async () => {
      called = true;
      return {} as Response;
    });

    assert.equal(called, false);
    assert.deepEqual(airports, []);
  });
});
