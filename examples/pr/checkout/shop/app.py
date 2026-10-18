"""Routes requests to handlers, behind authentication and idempotency."""
import re
from dataclasses import dataclass, field

from shop.middleware import AuthMiddleware, IdempotencyMiddleware


@dataclass
class Request:
    method: str
    path: str
    headers: dict = field(default_factory=dict)
    body: dict = field(default_factory=dict)
    user: str = ""


class Router:
    def __init__(self):
        self._routes = []

    def add(self, method, pattern, handler):
        self._routes.append((method, re.compile("^%s$" % pattern), handler))

    def __call__(self, request):
        for method, rx, handler in self._routes:
            m = rx.match(request.path)
            if m and method == request.method:
                return handler(request, *m.groups())
        return {"status": 404, "body": {"error": "no route"}}


def build(orders, payments, refunds, tokens):
    router = Router()
    router.add("GET", r"/orders/([\w-]+)", lambda req, oid: {"status": 200, "body": orders.get(oid)})
    router.add("POST", r"/orders/([\w-]+)/refunds", refunds.post)
    return AuthMiddleware(IdempotencyMiddleware(router), tokens)
