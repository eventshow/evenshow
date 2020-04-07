from django import template
from django.contrib.auth import get_user_model

from events.models import Event, Rating

register = template.Library()
User = get_user_model()


@register.simple_tag
def user_on_event(user: User, event: Event) -> Rating:
    return Rating.objects.filter(created_by=user, event=event).values_list('score', flat=True).first()
