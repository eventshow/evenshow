from datetime import time

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from . import models

User = get_user_model()


class EnrollmentSelector:
    def on_event(self, event_pk: int, status: str) -> QuerySet:
        return models.Enrollment.objects.filter(event__pk=event_pk, status=status)

    def user_on_event(self, user: User, event_pk: int) -> models.Enrollment:
        return models.Enrollment.objects.filter(event__pk=event_pk, created_by=user).first()


class EventSelector:
    def hosted(self, host: User) -> QuerySet:
        hosted_events = models.Event.objects.filter(
            created_by=host).order_by('title')
        return hosted_events

    def enrolled(self, attendee: User, status='ACCEPTED') -> QuerySet:
        enrolled_events = models.Event.objects.filter(
            event_enrollments__created_by=attendee).order_by('title')
        return enrolled_events

    def not_enrolled(self, attendee: User) -> QuerySet:
        not_enrolled_events = models.Event.objects.exclude(
            event_enrollments__created_by=attendee)
        return not_enrolled_events

    def location_date_start_hour(self, location: str, date: str, start_hour: time) -> QuerySet:
        return models.Event.objects.filter(location_city__iexact=location, start_day=date, start_time__gte=start_hour)

    def location(self, location: str) -> QuerySet:
        return models.Event.objects.filter(location_city__iexact=location)

    def date(self, date: str) -> QuerySet:
        return models.Event.objects.filter(start_day=date)

    def rated_by_user(self, user: User, on='HOST') -> QuerySet:
        return models.Event.objects.filter(ratings__created_by=user, ratings__on=on)

    def start_hour(self, start_hour: time) -> QuerySet:
        return models.Event.objects.filter(start_time__gte=start_hour)

    def location_start_hour(self, location: str, start_hour: time) -> QuerySet:
        return models.Event.objects.filter(location_city__iexact=location, start_time__gte=start_hour)

    def date_start_hour(self, date: str, start_hour: time) -> QuerySet:
        return models.Event.objects.filter(start_day=date, start_time__gte=start_hour)

    def location_date(self, location: str, date: str, ) -> QuerySet:
        return models.Event.objects.filter(location_city__iexact=location, start_day=date)

    def event_enrolled_accepted(self, attendee: User, status='ACCEPTED') -> QuerySet:
        event_enrolled_accepted = models.Event.objects.filter(
            event_enrollments__created_by=attendee, event_enrollments__status=status).order_by('title')
        return event_enrolled_accepted


class RatingSelector:
    def on_user(self, reviewed: User, on='HOST') -> QuerySet:
        return models.Rating.objects.filter(reviewed=reviewed, on=on)

    def exists_this_rating_for_this_user_and_event(self, created_by: User, event: models.Event,
                                                   reviewed: User) -> QuerySet:
        exists = models.Rating.objects.filter(created_by=created_by, event=event,
                                              reviewed=reviewed).exists()
        return exists


class UserSelector:
    def event_host(self, event_pk: int) -> QuerySet:
        host = User.objects.filter(host_events=event_pk).first()
        return host

    def event_attendees(self, event_pk: int) -> QuerySet:
        event_attendees = User.objects.filter(
            attendee_enrollments__event__pk=event_pk, attendee_enrollments__status='ACCEPTED').order_by('username')
        return event_attendees

    def rated_on_event(self, event_pk: int) -> QuerySet:
        return User.objects.filter(reviewed_ratings__event=event_pk)


class TransactionSelector:
    def my_transaction(self, user: User) -> QuerySet:
        transaction_list = models.Transaction.objects.filter(
            created_by=user).order_by('amount')
        return transaction_list
