"""Whether an order may be refunded this amount."""


class Refused(Exception):
    pass


class RefundPolicy:
    def check(self, order, request):
        if not order.paid:
            raise Refused("order %s was never paid" % order.id)
        try:
            order.refundable().minus(request.amount)
        except ValueError:
            raise Refused("only %s of order %s is left to refund" % (order.refundable(), order.id))
