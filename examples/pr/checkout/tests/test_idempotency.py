import unittest

from shop.app import Request
from shop.middleware import IdempotencyMiddleware


class Counter:
    def __init__(self):
        self.n = 0

    def __call__(self, request):
        self.n += 1
        return {"status": 201, "body": {"n": self.n}}


class IdempotencyTests(unittest.TestCase):
    def test_same_key_replays_the_first_response(self):
        inner = Counter()
        mw = IdempotencyMiddleware(inner)
        a = mw(Request("POST", "/x", {"Idempotency-Key": "k"}))
        b = mw(Request("POST", "/x", {"Idempotency-Key": "k"}))
        self.assertEqual(a, b)
        self.assertEqual(inner.n, 1)

    def test_same_key_on_two_routes_is_two_requests(self):
        inner = Counter()
        mw = IdempotencyMiddleware(inner)
        mw(Request("POST", "/x", {"Idempotency-Key": "k"}))
        mw(Request("POST", "/y", {"Idempotency-Key": "k"}))
        self.assertEqual(inner.n, 2)

    def test_a_5xx_is_not_replayed(self):
        calls = []

        def flaky(request):
            calls.append(1)
            return {"status": 503 if len(calls) == 1 else 201, "body": {}}
        mw = IdempotencyMiddleware(flaky)
        mw(Request("POST", "/x", {"Idempotency-Key": "k"}))
        self.assertEqual(mw(Request("POST", "/x", {"Idempotency-Key": "k"}))["status"], 201)
