"""Exact-decimal money value object.

Money is never represented with binary floating point (PHASE.md §Exact Money
Representation, CLAUDE.md engineering rules). All amounts are :class:`decimal.Decimal`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_CENTS = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money:
    """An amount of money in a single currency, using exact decimal arithmetic."""

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Money.amount must be a Decimal, never float")
        if self.amount < 0:
            raise ValueError("Money.amount must be nonnegative")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("Money.currency must be a 3-letter code")
        # Normalize currency to uppercase without mutating a frozen instance elsewhere.
        object.__setattr__(self, "currency", self.currency.upper())

    def quantized(self) -> Decimal:
        """Return the amount rounded to cents (half-up)."""
        return self.amount.quantize(_CENTS, rounding=ROUND_HALF_UP)

    def __mul__(self, factor: int) -> Money:
        if not isinstance(factor, int):
            raise TypeError("Money can only be multiplied by an int segment count")
        return Money(self.amount * factor, self.currency)

    __rmul__ = __mul__
