from datetime import time

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from . import models

User = get_user_model()


class EnrollmentSelector:
    def on_event(self, event_pk: int, status: str) -> QuerySet:
        return models.Enrollment.objects.filter(event__pk=event_pk, status=status)

    def enrolled_for_this_event(self, created_by: User, event: models.Event, status='ACCEPTED') -> QuerySet:
        enrolled_events = models.Enrollment.objects.filter(
            created_by=created_by, status=status, event=event).exists()
        return enrolled_events


class EventSelector:
    def hosted(host: User) -> QuerySet:
        hosted_events = models.Event.objects.filter(created_by=host)
        return hosted_events

    def is_owner(host: User, event_id: int) -> QuerySet:
        hosted_events = models.Event.objects.filter(
            created_by=host, id=event_id).exists()
        return hosted_events

    def enrolled(attendee: User, status='ACCEPTED') -> QuerySet:
        enrolled_events = models.Event.objects.filter(
            event_enrollments__created_by=attendee)
        return enrolled_events

    def not_enrolled(attendee: User) -> QuerySet:
        not_enrolled_events = models.Event.objects.exclude(
            event_enrollments__created_by=attendee)
        return not_enrolled_events

    def with_enrollment(enrollment_pk: int) -> models.Event:
        return models.Event.objects.filter(event_enrollments=enrollment_pk)

    def location_date_start_hour(self, location: str, date: str, start_hour: time) -> QuerySet:
        return models.Event.objects.filter(location_city__iexact=location, start_day=date, start_time__gte=start_hour)

    def location(self, location: str) -> QuerySet:
        return models.Event.objects.filter(location_city__iexact=location)

    def date(self, date: str) -> QuerySet:
        return models.Event.objects.filter(start_day=date)

    def start_hour(self, start_hour: time) -> QuerySet:
        return models.Event.objects.filter(start_time__gte=start_hour)

    def location_start_hour(self, location: str, start_hour: time) -> QuerySet:
        return models.Event.objects.filter(location_city__iexact=location, start_time__gte=start_hour)

    def date_start_hour(self, date: str, start_hour: time) -> QuerySet:
        return models.Event.objects.filter(start_day=date, start_time__gte=start_hour)

    def location_date(self, location: str, date: str,) -> QuerySet:
        return models.Event.objects.filter(location_city__iexact=location, start_day=date)


class RatingSelector:
    def on_event(event_pk: int, on='HOST') -> QuerySet:
        return models.Rating.objects.filter(event__pk=event_pk, on=on)

    def exists_this_rating_for_this_user_and_event(created_by: User, event: models.Event, reviewed: User) -> QuerySet:
        exists = models.Rating.objects.filter(created_by=created_by, event=event,
                                              reviewed=reviewed).exists()
        return exists


class UserSelector():
    def event_host(self, event_pk: int) -> QuerySet:
        host = User.objects.filter(host_events=event_pk).first()
        return host

    def event_attendees(self, event_pk: int) -> QuerySet:
        event_attendees = User.objects.filter(
            attendee_enrollments__event__pk=event_pk, attendee_enrollments__status='ACCEPTED')
        return event_attendees

    def enrolled_for_this_event(self, created_by: User, event: models.Event, status='ACCEPTED') -> QuerySet:
        enrolled_events = models.Enrollment.objects.filter(
            created_by=created_by, status=status, event=event).exists()
        return enrolled_events
