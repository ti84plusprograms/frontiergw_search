"""Routing performance benchmark (PHASE.md §Performance Requirements).

Benchmark environment and dataset (documented per the contract):
  * Dataset: a synthetic hub 'ATL' with up to 6 direct spokes, each spoke having up to
    5 onward departures, on a single operating date within one active schedule version.
    Small by design — the benchmark validates the ACCESS PATTERN (bounded query count,
    <= 1 connection), not raw throughput at production scale.
  * Environment: the CI PostgreSQL service (or a local Postgres). Numbers are p95 over
    repeated in-process searches; they characterize the engine + DB access path, not
    network/API latency.

Targets: direct-only p95 < 250 ms; direct + one-stop p95 < 1000 ms. Per the contract,
a slow wall-clock number does not by itself block the phase; the hard assertions here
are the algorithmic ones: query count is BOUNDED (no per-result N+1) and traversal is
bounded to <= 1 connection. Timing is reported and softly asserted with generous room.

Skipped on SQLite (requires PostgreSQL + SMALLINT[] arrays).
"""

from __future__ import annotations

import os
import time as _time
from datetime import date, time

import pytest
from sqlalchemy import event

from app.schemas.search import SearchCriteria
from app.services.routing.engine import search_itineraries
from tests.routing_fixtures import add_flight, make_source, seed_airports

_DB_URL = os.getenv("DATABASE_URL_TEST", os.getenv("DATABASE_URL", "sqlite:///:memory:"))
pytestmark = pytest.mark.skipif(
    "sqlite" in _DB_URL, reason="routing performance benchmark requires PostgreSQL"
)

TUESDAY = date(2026, 8, 4)


def _seed_hub(db_session, *, spokes: int, onward: int) -> None:
    """Seed ATL -> N spokes, each spoke -> M onward domestic destinations."""
    seed_airports(db_session)
    src = make_source(db_session, version="perf-v1", is_active=True)
    # Reuse the small synthetic airport set as spokes/onward endpoints cyclically.
    from tests.routing_fixtures import AIRPORTS

    codes = [c for c, _country, _tz in AIRPORTS if c != "ATL"]
    fnum = 0
    for i in range(spokes):
        spoke = codes[i % len(codes)]
        if spoke == "ATL":
            continue
        fnum += 1
        dep_h = 6 + i % 4
        add_flight(
            db_session,
            src,
            origin="ATL",
            destination=spoke,
            dep=time(dep_h, (i * 7) % 60),
            arr=time(dep_h + 2, (i * 7) % 60),
            arrival_day_offset=0,
            flight_number=str(1000 + fnum),
        )
        for j in range(onward):
            dest = codes[(i + j + 1) % len(codes)]
            if dest in {"ATL", spoke}:
                continue
            fnum += 1
            add_flight(
                db_session,
                src,
                origin=spoke,
                destination=dest,
                dep=time(dep_h + 3 + j % 3, (j * 11) % 60),
                arr=time(dep_h + 4 + j % 3, (j * 11) % 60),
                arrival_day_offset=0,
                flight_number=str(1000 + fnum),
            )
    db_session.flush()


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    idx = max(0, int(round(0.95 * (len(ordered) - 1))))
    return ordered[idx]


def _count_queries(bind):
    counter = {"n": 0}

    def _before(conn, cursor, statement, params, context, executemany):  # noqa: ANN001
        counter["n"] += 1

    event.listen(bind, "before_cursor_execute", _before)
    return counter, _before


def _direct_query_count(db_session, spokes: int) -> tuple[int, int, float]:
    _seed_hub(db_session, spokes=spokes, onward=0)
    bind = db_session.get_bind()
    counter, listener = _count_queries(bind)
    try:
        samples = []
        result = None
        for _ in range(20):
            counter["n"] = 0
            t0 = _time.perf_counter()
            result = search_itineraries(
                db_session,
                SearchCriteria(origin="ATL", departure_date=TUESDAY, max_connections=0),
            )
            samples.append(_time.perf_counter() - t0)
    finally:
        event.remove(bind, "before_cursor_execute", listener)
    assert result is not None and result.itineraries, "expected direct results"
    return counter["n"], len(result.itineraries), _p95(samples)


def test_direct_search_query_count_is_constant_no_n_plus_1(db_session):
    # The N+1 guarantee: query count for direct-only search does NOT grow with the
    # number of results/spokes. Measured at two dataset sizes; counts must match.
    small_q, small_r, _ = _direct_query_count(db_session, spokes=3)
    # Clear flights AND the source, so reseeding a larger dataset does not violate the
    # single-active-source constraint or flight uniqueness (same rolled-back txn).
    from app.db.models.data_source import DataSource
    from app.db.models.scheduled_flight import ScheduledFlight

    db_session.query(ScheduledFlight).delete()
    db_session.query(DataSource).delete()
    db_session.flush()
    large_q, large_r, p95 = _direct_query_count(db_session, spokes=6)

    assert large_r > small_r, "larger dataset should yield more results"
    assert small_q == large_q, (
        f"direct query count grew with results ({small_q}->{large_q}): N+1 pattern"
    )
    assert p95 < 2.0, f"direct p95 {p95:.3f}s far exceeds target (target 0.25s)"
    print(f"[perf] direct-only p95={p95 * 1000:.1f}ms constant_queries={large_q}")


def test_one_stop_search_p95_and_bounded_traversal(db_session):
    _seed_hub(db_session, spokes=6, onward=5)
    samples = []
    for _ in range(10):
        t0 = _time.perf_counter()
        result = search_itineraries(
            db_session, SearchCriteria(origin="ATL", departure_date=TUESDAY, max_connections=1)
        )
        samples.append(_time.perf_counter() - t0)
    p95 = _p95(samples)

    # Bounded traversal: no itinerary exceeds one connection (<= 2 segments).
    assert all(it.connection_count <= 1 for it in result.itineraries)
    assert p95 < 3.0, f"one-stop p95 {p95:.3f}s far exceeds target (target 1.0s)"
    print(f"[perf] direct+one-stop p95={p95 * 1000:.1f}ms results={len(result.itineraries)}")
