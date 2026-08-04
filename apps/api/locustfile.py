"""Synthetic-only Phase 5 workload. Never contacts Frontier or another provider."""

from __future__ import annotations

from itertools import count

from locust import HttpUser, between, task

DIRECT = {"origin": "ATL", "departure_date": "2026-08-04", "max_connections": 0}
CONNECTING = {"origin": "ATL", "departure_date": "2026-08-04", "max_connections": 1}


class SyntheticSearchUser(HttpUser):
    wait_time = between(0.1, 0.5)
    sequence = count()
    client_sequence = count(1)

    def on_start(self) -> None:
        client_number = (next(self.client_sequence) - 1) % 254 + 1
        self.search_headers = {"X-Forwarded-For": f"198.51.100.{client_number}"}

    @task(4)
    def cached_search(self) -> None:
        self.client.post(
            "/api/v1/search",
            json=DIRECT,
            headers=self.search_headers,
            name="search/cached-direct",
        )

    @task(2)
    def uncached_direct(self) -> None:
        value = next(self.sequence) % 1000
        self.client.post(
            "/api/v1/search",
            json={**DIRECT, "max_price": f"{1000 + value}.00"},
            headers=self.search_headers,
            name="search/uncached-direct",
        )

    @task(2)
    def uncached_connecting(self) -> None:
        value = next(self.sequence) % 1000
        self.client.post(
            "/api/v1/search",
            json={**CONNECTING, "max_price": f"{2000 + value}.00"},
            headers=self.search_headers,
            name="search/uncached-connecting",
        )

    @task
    def no_results(self) -> None:
        self.client.post(
            "/api/v1/search",
            json={"origin": "ORL", "departure_date": "2026-08-04", "max_connections": 0},
            headers=self.search_headers,
            name="search/no-results",
        )

    @task(2)
    def airport_lookup(self) -> None:
        self.client.get("/api/v1/airports?query=ATL&limit=10", name="airports")

    @task
    def schedule_status(self) -> None:
        self.client.get("/api/v1/schedules/status", name="schedule-status")

    @task
    def rate_burst(self) -> None:
        with self.client.post(
            "/api/v1/search",
            json=DIRECT,
            headers={"X-Forwarded-For": "203.0.113.1"},
            name="search/rate-burst",
            catch_response=True,
        ) as response:
            if response.status_code in {200, 429}:
                response.success()
