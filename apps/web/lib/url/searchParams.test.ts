import {
  parseSearchParams,
  serializeSearchParams,
  toSearchRequest,
  type SearchCriteriaState,
} from "@/lib/url/searchParams";
import { describe, expect, it } from "vitest";

const COMPLETE: SearchCriteriaState = {
  origin: "atl",
  date: "2026-08-04",
  connections: 1,
  minConnMinutes: 60,
  maxConnMinutes: 300,
  departAfter: "06:00",
  departBefore: "22:00",
  arriveBefore: "23:30",
  maxDuration: 900,
  maxPrice: 12.5,
  domesticOnly: true,
  sort: "TOTAL_DURATION",
};

describe("search URL state", () => {
  it("round-trips every request criterion including decimal prices", () => {
    const parsed = parseSearchParams(serializeSearchParams(COMPLETE));
    expect(parsed).toEqual({ ...COMPLETE, origin: "ATL", internationalOnly: undefined });
    expect(parsed?.maxPrice).toBe(12.5);
  });

  it("maps normalized state to the complete backend request", () => {
    expect(toSearchRequest(COMPLETE)).toEqual({
      origin: "ATL",
      departure_date: "2026-08-04",
      max_connections: 1,
      min_connection_minutes: 60,
      max_connection_minutes: 300,
      depart_after: "06:00",
      depart_before: "22:00",
      arrive_before: "23:30",
      max_total_duration_minutes: 900,
      max_price: 12.5,
      domestic_only: true,
      international_only: false,
      sort: "TOTAL_DURATION",
    });
  });

  it.each([
    "origin=ATL&date=2026-02-30",
    "origin=ATL&date=2026-08-04&connections=garbage",
    "origin=ATL&date=2026-08-04&min_conn=19",
    "origin=ATL&date=2026-08-04&max_conn=361",
    "origin=ATL&date=2026-08-04&min_conn=240&max_conn=45",
    "origin=ATL&date=2026-08-04&max_duration=1441",
    "origin=ATL&date=2026-08-04&max_price=-1",
    "origin=ATL&date=2026-08-04&depart_after=25:00",
    "origin=ATL&date=2026-08-04&domestic=1&international=1",
    "origin=ATL&date=2026-08-04&sort=CHEAPEST",
  ])("rejects an invalid shared URL: %s", (query) => {
    expect(parseSearchParams(new URLSearchParams(query))).toBeNull();
  });

  it("normalizes omitted defaults without changing request behavior", () => {
    const parsed = parseSearchParams(new URLSearchParams("origin=atl&date=2026-08-04"));
    expect(parsed).toMatchObject({ origin: "ATL", connections: 0, sort: "PRICE" });
    expect(toSearchRequest(parsed!)).toMatchObject({
      min_connection_minutes: 45,
      max_connection_minutes: 240,
      max_total_duration_minutes: 720,
    });
  });
});
