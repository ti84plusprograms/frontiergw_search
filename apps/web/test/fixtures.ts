import type { ItineraryModel, SearchResponse } from "@/lib/api/client";

export function itinerary(
  overrides: Partial<ItineraryModel> = {},
): ItineraryModel {
  return {
    itinerary_id: "iti-direct",
    origin: { code: "ATL", city: "Atlanta", country_code: "US" },
    destination: { code: "DEN", city: "Denver", country_code: "US" },
    departure_at: "2026-08-04T09:35:00-04:00",
    arrival_at: "2026-08-04T11:05:00-06:00",
    connection_count: 0,
    total_duration_minutes: 210,
    airborne_duration_minutes: 210,
    total_layover_minutes: 0,
    segments: [
      {
        sequence: 1,
        carrier: "F9",
        flight_number: "1234",
        origin: "ATL",
        destination: "DEN",
        departure_at: "2026-08-04T09:35:00-04:00",
        arrival_at: "2026-08-04T11:05:00-06:00",
        duration_minutes: 210,
      },
    ],
    price: {
      amount: "14.91",
      currency: "USD",
      status: "ESTIMATED",
      segment_count: 1,
      verified_at: null,
      disclaimer:
        "Final taxes, fees, and GoWild availability must be confirmed with Frontier.",
    },
    availability: {
      status: "NOT_CHECKED",
      checked_at: null,
      source: null,
      confidence: "LOW",
    },
    booking_url: null,
    ...overrides,
  };
}

export function searchResponse(
  results: ItineraryModel[] = [itinerary()],
): SearchResponse {
  return {
    search_id: "srch-test",
    origin: { code: "ATL", city: "Atlanta", timezone: "America/New_York" },
    departure_date: "2026-08-04",
    generated_at: "2026-08-01T12:00:00+00:00",
    data_freshness: {
      schedule_source: "synthetic",
      schedule_version: "v1",
      schedule_updated_at: "2026-08-01T12:00:00+00:00",
      schedule_effective_start: "2026-08-01",
      schedule_effective_end: "2026-10-31",
      availability_checked_at: null,
    },
    result_count: results.length,
    results,
    warnings: [
      { code: "AVAILABILITY_NOT_CHECKED", message: "GoWild availability has not been verified." },
    ],
  };
}
