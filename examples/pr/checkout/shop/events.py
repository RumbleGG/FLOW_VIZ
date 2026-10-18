"""In-process events: a name and a payload, delivered to every subscriber in order."""


class EventPublisher:
    def __init__(self):
        self._subs = []

    def subscribe(self, fn):
        self._subs.append(fn)

    def publish(self, name, payload):
        for fn in self._subs:
            fn(name, payload)
