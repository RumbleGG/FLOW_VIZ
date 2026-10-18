"""Request middleware: who is calling, and whether this request has been seen before."""
import hashlib


class AuthMiddleware:
    def __init__(self, inner, tokens):
        self.inner = inner
        self.tokens = tokens

    def __call__(self, request):
        who = self.tokens.get(request.headers.get("Authorization", ""))
        if who is None:
            return {"status": 401, "body": {"error": "unauthorized"}}
        request.user = who
        return self.inner(request)


class IdempotencyMiddleware:
    """Replays the stored response when a POST arrives again with the same Idempotency-Key."""

    def __init__(self, inner):
        self.inner = inner
        self._seen = {}

    def key(self, request):
        raw = request.headers.get("Idempotency-Key")
        if not raw:
            return None
        return hashlib.sha256(("%s %s %s" % (request.method, request.path, raw)).encode()).hexdigest()

    def __call__(self, request):
        if request.method != "POST":
            return self.inner(request)
        k = self.key(request)
        if k is None:
            return self.inner(request)
        if k in self._seen:
            return self._seen[k]
        response = self.inner(request)
        if response["status"] < 500:
            self._seen[k] = response
        return response
