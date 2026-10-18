"""What a refund request says, checked before anything is looked up."""
from dataclasses import dataclass

from shop.money import Money


class BadRequest(ValueError):
    pass


@dataclass(frozen=True)
class RefundRequest:
    order_id: str
    amount: Money
    reason: str

    @classmethod
    def parse(cls, order_id, body):
        try:
            cents = int(body["amount_cents"])
        except (KeyError, TypeError, ValueError):
            raise BadRequest("amount_cents must be a whole number of cents")
        if cents <= 0:
            raise BadRequest("amount_cents must be above zero")
        reason = str(body.get("reason", "")).strip()
        if not reason:
            raise BadRequest("a reason is required")
        return cls(order_id, Money(cents), reason[:200])
