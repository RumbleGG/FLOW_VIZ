"""Refunds that were issued, one row each."""
import itertools


class RefundStore:
    def __init__(self):
        self._rows = []
        self._ids = itertools.count(1)

    def save(self, order, request, provider_id):
        row = {"id": "rf_%d" % next(self._ids), "order": order.id, "amount_cents": request.amount.cents,
               "reason": request.reason, "provider_id": provider_id}
        self._rows.append(row)
        order.refunded = order.refunded.plus(request.amount)
        return row
