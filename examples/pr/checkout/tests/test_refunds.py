import unittest

from shop.app import Request, build
from shop.audit import AuditLog
from shop.events import EventPublisher
from shop.money import Money
from shop.orders import Order, OrderRepository
from shop.payments import HttpTransport, PaymentClient
from shop.refunds.handler import RefundHandler
from shop.refunds.policy import RefundPolicy
from shop.refunds.store import RefundStore
from tests.fakes import FakeProvider


def shop(provider=None):
    orders = OrderRepository()
    orders.add(Order("o-1", "c-9", Money(5000), paid=True, charge_id="ch_1"))
    orders.add(Order("o-2", "c-9", Money(1200)))
    events = EventPublisher()
    log = AuditLog(events)
    payments = PaymentClient(HttpTransport(provider or FakeProvider()))
    handler = RefundHandler(orders, RefundPolicy(), payments, RefundStore(), events)
    return build(orders, payments, handler, {"Bearer t": "support"}), orders, log


def post(app, path, body, key="k-1"):
    headers = {"Authorization": "Bearer t"}
    if key:
        headers["Idempotency-Key"] = key
    return app(Request("POST", path, headers, body))


class RefundTests(unittest.TestCase):
    def test_refund_part_of_a_paid_order(self):
        app, orders, log = shop()
        r = post(app, "/orders/o-1/refunds", {"amount_cents": 1500, "reason": "arrived late"})
        self.assertEqual(r["status"], 201)
        self.assertEqual(orders.get("o-1").refundable(), Money(3500))
        self.assertEqual(log.rows[-1][0], "refund.issued")

    def test_refuse_more_than_is_left(self):
        app, _, _ = shop()
        r = post(app, "/orders/o-1/refunds", {"amount_cents": 6000, "reason": "arrived late"})
        self.assertEqual(r["status"], 422)

    def test_refuse_an_unpaid_order(self):
        app, _, _ = shop()
        r = post(app, "/orders/o-2/refunds", {"amount_cents": 100, "reason": "arrived late"})
        self.assertEqual(r["status"], 422)

    def test_same_key_refunds_once(self):
        app, orders, _ = shop()
        a = post(app, "/orders/o-1/refunds", {"amount_cents": 1500, "reason": "arrived late"})
        b = post(app, "/orders/o-1/refunds", {"amount_cents": 1500, "reason": "arrived late"})
        self.assertEqual(a, b)
        self.assertEqual(orders.get("o-1").refundable(), Money(3500))

    def test_require_an_idempotency_key(self):
        app, _, _ = shop()
        r = post(app, "/orders/o-1/refunds", {"amount_cents": 100, "reason": "arrived late"}, key=None)
        self.assertEqual(r["status"], 400)
