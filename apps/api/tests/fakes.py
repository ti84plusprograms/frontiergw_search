"""Small deterministic Redis fake for cache/rate-limit tests."""

from __future__ import annotations

from threading import Lock


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.counts: dict[str, int] = {}
        self._lock = Lock()

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(
        self,
        key: str,
        value: str,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool:
        with self._lock:
            if nx and key in self.values:
                return False
            self.values[key] = value
            if ex is not None:
                self.ttls[key] = ex
            return True

    def delete(self, key: str) -> int:
        existed = key in self.values
        self.values.pop(key, None)
        self.ttls.pop(key, None)
        self.counts.pop(key, None)
        return int(existed)

    def scan_iter(self, *, match: str, count: int):  # noqa: ARG002
        prefix = match.removesuffix("*")
        yield from [key for key in self.values if key.startswith(prefix)]

    def eval(self, script: str, number_of_keys: int, key: str, *args: object):  # noqa: ARG002
        with self._lock:
            if "INCR" in script:
                self.counts[key] = self.counts.get(key, 0) + 1
                return [self.counts[key], int(args[0])]
            token = str(args[0])
            if self.values.get(key) == token:
                return self.delete(key)
            return 0

    def ping(self) -> bool:
        return True


class ExplodingRedis:
    def __getattr__(self, name: str):
        def explode(*args: object, **kwargs: object):  # noqa: ARG001
            raise TimeoutError(f"synthetic Redis {name} timeout")

        return explode
