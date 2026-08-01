"""Direct and one-stop itinerary generation (RTE-002, RTE-003).

Uses the schedule repository (active-source-scoped, no N+1), the RTE-001 resolver,
the connection validator (RTE-004), and the price estimator (RTE-007). Airport
metadata is bulk-loaded once per search for timezones and country codes.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from app.db.models.airport import Airport
from app.db.models.scheduled_flight import ScheduledFlight
from app.domain.flight_instance import FlightInstance
from app.domain.itinerary import Itinerary, ItinerarySegment
from app.repositories.schedule import ScheduleRepository
from app.services.routing.connections import ConnectionPolicy, validate_connection
from app.services.routing.instances import ResolutionSkip, resolve_instance
from app.services.routing.pricing import PriceEstimator


class ItineraryFactory:
    """Builds priced itineraries from resolved flight instances."""

    def __init__(self, estimator: PriceEstimator, airports: dict[str, Airport]) -> None:
        self._estimator = estimator
        self._airports = airports

    def _is_international(self, codes: list[str]) -> bool:
        countries = {self._airports[c].country_code for c in codes if c in self._airports}
        return len(countries) > 1

    def build_direct(self, first: FlightInstance) -> Itinerary:
        price = self._estimator.estimate(
            1, is_international=self._is_international([first.origin_code, first.destination_code])
        )
        return Itinerary(
            origin_code=first.origin_code,
            destination_code=first.destination_code,
            segments=(ItinerarySegment(sequence=1, flight=first),),
            price=price,
        )

    def build_one_stop(self, first: FlightInstance, second: FlightInstance) -> Itinerary:
        codes = [first.origin_code, first.destination_code, second.destination_code]
        price = self._estimator.estimate(2, is_international=self._is_international(codes))
        return Itinerary(
            origin_code=first.origin_code,
            destination_code=second.destination_code,
            segments=(
                ItinerarySegment(sequence=1, flight=first),
                ItinerarySegment(sequence=2, flight=second),
            ),
            price=price,
        )


class SearchDiagnostics:
    """Observability counters (PHASE.md §Logging). No PII."""

    def __init__(self) -> None:
        self.first_segment_candidates = 0
        self.second_segment_candidates = 0
        self.rejected_connections = 0
        self.missing_airport_metadata = 0
        self.resolution_skips: dict[str, int] = {}

    def record_resolution_skip(self, reason: str) -> None:
        self.resolution_skips[reason] = self.resolution_skips.get(reason, 0) + 1


def _resolve_all(
    flights_with_dates: Sequence[tuple[ScheduledFlight, date]],
    repo_airports: dict[str, Airport],
    diagnostics: SearchDiagnostics | None = None,
) -> list[FlightInstance]:
    diag = diagnostics or SearchDiagnostics()
    instances: list[FlightInstance] = []
    for flight, service_date in flights_with_dates:
        origin = repo_airports.get(flight.origin_code)
        dest = repo_airports.get(flight.destination_code)
        if origin is None or dest is None:
            diag.missing_airport_metadata += 1
            continue
        resolved = resolve_instance(flight, service_date, origin, dest)
        if isinstance(resolved, ResolutionSkip):
            diag.record_resolution_skip(resolved.reason)
            continue
        instances.append(resolved)
    return instances


def generate_itineraries(
    repo: ScheduleRepository,
    origin: str,
    departure_date: date,
    *,
    max_connections: int,
    policy: ConnectionPolicy,
    estimator: PriceEstimator,
    airports: dict[str, Airport],
    diagnostics: SearchDiagnostics | None = None,
) -> list[Itinerary]:
    """Generate direct (and, when allowed, one-stop) itineraries. Unfiltered/unsorted."""
    diag = diagnostics or SearchDiagnostics()
    factory = ItineraryFactory(estimator, airports)

    first_flights = repo.find_departures(origin, departure_date)
    first_instances = _resolve_all(
        [(f, departure_date) for f in first_flights], airports, diagnostics=diag
    )
    diag.first_segment_candidates = len(first_instances)

    itineraries: list[Itinerary] = []
    for first in first_instances:
        if first.origin_code == first.destination_code:
            diag.record_resolution_skip("repeated_airport")
            continue
        itineraries.append(factory.build_direct(first))

        if max_connections < 1:
            continue

        candidate_dates = {
            first.arrival_at.date(),
            first.arrival_at.date() + timedelta(days=1),
        }
        second_pairs = repo.find_departures_for_dates(first.destination_code, candidate_dates)
        second_instances = _resolve_all(second_pairs, airports, diagnostics=diag)
        diag.second_segment_candidates += len(second_instances)

        for second in second_instances:
            result = validate_connection(first, second, origin, policy)
            if not result.is_valid:
                diag.rejected_connections += 1
                continue
            itineraries.append(factory.build_one_stop(first, second))

    return itineraries
