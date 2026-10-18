"""A provider that answers from a script of statuses, and remembers every call."""


class FakeProvider:
    def __init__(self, statuses=None):
        self.calls = []
        self.statuses = list(statuses or [])

    def __call__(self, path, body, headers):
        self.calls.append((path, body, headers))
        status = self.statuses.pop(0) if self.statuses else 201
        return status, ({"id": "pv_%d" % len(self.calls)} if status == 201 else {"error": "busy"})
