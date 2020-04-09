from django import template

register = template.Library()


@register.simple_tag
def to_euros(cents: float) -> float:
    return round(cents/100, 2)