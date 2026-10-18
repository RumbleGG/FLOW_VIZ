"""Every event, kept in the order it happened."""


class AuditLog:
    def __init__(self, events):
        self.rows = []
        events.subscribe(self.record)

    def record(self, name, payload):
        self.rows.append((name, dict(payload)))
