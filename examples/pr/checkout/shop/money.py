"""Amounts of money, held as integer cents so nothing is lost to floating point."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    cents: int
    currency: str = "USD"

    def plus(self, other):
        self._same(other)
        return Money(self.cents + other.cents, self.currency)

    def minus(self, other):
        self._same(other)
        if other.cents > self.cents:
            raise ValueError("%s minus %s would go below zero" % (self, other))
        return Money(self.cents - other.cents, self.currency)

    def _same(self, other):
        if other.currency != self.currency:
            raise ValueError("cannot mix %s and %s" % (self.currency, other.currency))

    def __str__(self):
        return "%s %d.%02d" % (self.currency, self.cents // 100, self.cents % 100)
