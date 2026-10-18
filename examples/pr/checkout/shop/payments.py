"""Calls to the payment provider."""


class ProviderUnavailable(Exception):
    pass


class HttpTransport:
    """Posts JSON to the provider with an Idempotency-Key, which the provider dedupes on.
    A 503 is the provider shedding load: retried up to twice, with the same key."""

    RETRY_ON = (503,)

    def __init__(self, send, retries=2):
        self.send = send
        self.retries = retries

    def post(self, path, body, idempotency_key):
        headers = {"Idempotency-Key": idempotency_key}
        for attempt in range(self.retries + 1):
            status, reply = self.send(path, body, headers)
            if status not in self.RETRY_ON:
                return status, reply
        raise ProviderUnavailable("%s answered 503 %d times" % (path, self.retries + 1))


class PaymentClient:
    def __init__(self, transport):
        self.transport = transport

    def charge(self, order, key):
        status, reply = self.transport.post("/charges", {"amount": order.total.cents, "order": order.id}, key)
        if status != 201:
            raise RuntimeError("charge refused: %s" % reply.get("error"))
        return reply["id"]

    def refund(self, order, amount, key):
        status, reply = self.transport.post("/refunds", {"charge": order.charge_id, "amount": amount.cents}, key)
        if status != 201:
            raise RuntimeError("refund refused: %s" % reply.get("error"))
        return reply["id"]
