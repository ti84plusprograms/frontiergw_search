from typing import Any, cast

from sqlalchemy import JSON, SmallInteger, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY


class OperatingDaysType(TypeDecorator[list[int]]):
    """Use PostgreSQL SMALLINT[] while keeping unit tests SQLite-compatible."""

    impl = ARRAY(SmallInteger)
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "sqlite":
            return dialect.type_descriptor(JSON())
        return dialect.type_descriptor(ARRAY(SmallInteger))

    def process_bind_param(self, value: list[int] | None, dialect: Any) -> list[int] | None:
        return value

    def process_result_value(self, value: Any, dialect: Any) -> list[int] | None:
        return cast(list[int] | None, value)
