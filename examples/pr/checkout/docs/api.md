# API

Every call carries `Authorization: Bearer <token>`. A POST may carry `Idempotency-Key`; sending the
same key again replays the first response instead of doing the work twice.

## GET /orders/{id}

The order, or 404.

## POST /orders/{id}/refunds

Refunds part or all of a paid order to the card that paid it. Requires `Idempotency-Key`. Body:
`amount_cents` (above zero) and `reason`. Answers 201 with the refund, 400 for a bad body, 404 for no such order, and 422 when the order
was never paid or less than `amount_cents` is left to refund.
