from django import template

from events.models import Transaction

register = template.Library()


@register.simple_tag
def to_euros(dividend: float) -> float:
    return round(dividend / 100, 2)
