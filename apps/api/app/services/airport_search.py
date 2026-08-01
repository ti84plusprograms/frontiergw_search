"""Deterministic airport search (API-001).

Ranked, case-insensitive, whitespace-trimmed matching over active airports against
code / city / name / region, bounded by a result limit. Ranking priority and stable
tie-breakers are documented below (PHASE.md API-001 §Required Search Behavior).

Ranking (lower rank sorts first):
  0 exact airport-code match
  1 airport-code prefix match
  2 exact city match
  3 city prefix match
  4 airport-name substring match
  5 state/region substring match
Tie-breaker within a rank: airport code ascending (stable, deterministic).
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.airport import Airport


def _rank(airport: Airport, q: str) -> int | None:
    code = airport.code.upper()
    city = airport.city.casefold()
    name = airport.name.casefold()
    region = (airport.state_or_region or "").casefold()
    qc = q.casefold()
    qu = q.upper()

    if code == qu:
        return 0
    if code.startswith(qu):
        return 1
    if city == qc:
        return 2
    if city.startswith(qc):
        return 3
    if qc in name:
        return 4
    if region and qc in region:
        return 5
    return None


def search_airports(db: Session, query: str, limit: int) -> list[Airport]:
    """Return up to ``limit`` active airports ranked for ``query`` (deterministic)."""
    q = query.strip()
    if not q:
        return []

    like = f"%{q}%"
    prefix = f"{q}%"
    # Parameterized candidate filter (case-insensitive) done in SQL; precise ranking in
    # Python. ``ilike`` uses bound parameters — no raw SQL from user input.
    stmt = (
        select(Airport)
        .where(Airport.is_active.is_(True))
        .where(
            or_(
                Airport.code.ilike(prefix),
                Airport.city.ilike(like),
                Airport.name.ilike(like),
                Airport.state_or_region.ilike(like),
            )
        )
    )
    candidates = list(db.scalars(stmt).all())

    ranked: list[tuple[int, str, Airport]] = []
    for airport in candidates:
        rank = _rank(airport, q)
        if rank is not None:
            ranked.append((rank, airport.code.upper(), airport))

    ranked.sort(key=lambda item: (item[0], item[1]))
    return [airport for _, _, airport in ranked[:limit]]
