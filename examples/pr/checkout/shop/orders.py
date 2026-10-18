"""Orders and where they are kept."""
from dataclasses import dataclass, field

from shop.money import Money


@dataclass
class Order:
    id: str
    customer: str
    total: Money
    paid: bool = False
    charge_id: str = ""
    refunded: Money = field(default_factory=lambda: Money(0))

    def apply_discount(self, amount):
        self.total = self.total.minus(amount)

    def refundable(self):
        return self.total.minus(self.refunded)


class OrderRepository:
    def __init__(self):
        self._orders = {}

    def add(self, order):
        self._orders[order.id] = order

    def get(self, order_id):
        return self._orders.get(order_id)

    def save(self, order):
        self._orders[order.id] = order
