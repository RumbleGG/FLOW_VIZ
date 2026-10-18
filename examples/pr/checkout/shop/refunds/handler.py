"""POST /orders/{id}/refunds — refund part or all of a paid order."""
from shop.refunds.policy import Refused
from shop.refunds.request import BadRequest, RefundRequest


class RefundHandler:
    def __init__(self, orders, policy, payments, store, events):
        self.orders = orders
        self.policy = policy
        self.payments = payments
        self.store = store
        self.events = events

    def post(self, request, order_id):
        key = request.headers.get("Idempotency-Key")
        if not key:
            return {"status": 400, "body": {"error": "an Idempotency-Key header is required"}}
        try:
            refund = RefundRequest.parse(order_id, request.body)
        except BadRequest as e:
            return {"status": 400, "body": {"error": str(e)}}
        order = self.orders.get(order_id)
        if order is None:
            return {"status": 404, "body": {"error": "no order %s" % order_id}}
        try:
            self.policy.check(order, refund)
        except Refused as e:
            return {"status": 422, "body": {"error": str(e)}}
        provider_id = self.payments.refund(order, refund.amount, key)
        row = self.store.save(order, refund, provider_id)
        self.orders.save(order)
        self.events.publish("refund.issued", row)
        return {"status": 201, "body": row}
