from django import template

from events.services import PaymentService

register = template.Library()


@register.simple_tag
def apply_fee(cents: int):
    return cents + PaymentService().fee(cents)


@register.simple_tag
def to_euros(cents: int) -> float:
    return round(cents/100, 2)


@register.simple_tag
def to_cents(euros: float) -> int:
    return int(round(euros*100, 2))
