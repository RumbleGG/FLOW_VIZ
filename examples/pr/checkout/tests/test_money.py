import unittest

from shop.money import Money


class MoneyTests(unittest.TestCase):
    def test_plus_keeps_cents(self):
        self.assertEqual(Money(150).plus(Money(275)), Money(425))

    def test_currencies_never_mix(self):
        with self.assertRaises(ValueError):
            Money(1).plus(Money(1, "EUR"))

    def test_minus_refuses_to_go_below_zero(self):
        with self.assertRaises(ValueError):
            Money(100).minus(Money(101))
