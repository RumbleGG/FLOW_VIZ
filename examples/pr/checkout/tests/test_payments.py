import unittest

from shop.money import Money
from shop.orders import Order
from shop.payments import HttpTransport, PaymentClient, ProviderUnavailable
from tests.fakes import FakeProvider


class PaymentTests(unittest.TestCase):
    def test_charge_sends_the_key(self):
        provider = FakeProvider()
        PaymentClient(HttpTransport(provider)).charge(Order("o-1", "c-9", Money(900)), "k-1")
        self.assertEqual(provider.calls[0][2], {"Idempotency-Key": "k-1"})

    def test_retry_a_503_with_the_same_key(self):
        provider = FakeProvider([503, 201])
        PaymentClient(HttpTransport(provider)).charge(Order("o-1", "c-9", Money(900)), "k-1")
        self.assertEqual([c[2] for c in provider.calls], [{"Idempotency-Key": "k-1"}] * 2)

    def test_give_up_after_three_503s(self):
        provider = FakeProvider([503, 503, 503])
        with self.assertRaises(ProviderUnavailable):
            HttpTransport(provider).post("/refunds", {}, "k-1")
        self.assertEqual(len(provider.calls), 3)
