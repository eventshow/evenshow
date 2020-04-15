from django import template
from django.db.models import QuerySet

register = template.Library()


@register.filter
def accepted(enrollments) -> QuerySet:
    return enrollments.filter(status="ACCEPTED")
