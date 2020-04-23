import googlemaps

from collections import OrderedDict
from datetime import datetime, time, timedelta
from operator import itemgetter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, F, FloatField, Sum, Q, QuerySet
from django.db.models.functions import Cast

from . import models

User = get_user_model()


class EnrollmentSelector:
    def created_by(self, user: User) -> QuerySet:
        return models.Enrollment.objects.filter(created_by=user)

    def on_event(self, event_pk: int, status: str) -> QuerySet:
        return models.Enrollment.objects.filter(event__pk=event_pk, status=status)

    def user_on_event(self, user: User, event_pk: int) -> models.Enrollment:
        return models.Enrollment.objects.filter(event__pk=event_pk, created_by=user).first()


class EventSelector:
    def hosted(self, host: User) -> QuerySet:
        hosted_events = models.Event.objects.filter(
            created_by=host)
        return hosted_events

    def enrolled(self, attendee: User, status='ACCEPTED') -> QuerySet:
        enrolled_events = models.Event.objects.filter(
            event_enrollments__created_by=attendee)
        return enrolled_events

    def not_enrolled(self, attendee: User) -> QuerySet:
        not_enrolled_events = models.Event.objects.exclude(
            event_enrollments__created_by=attendee)
        return not_enrolled_events

    def not_started(self, events):
        now = datetime.now()
        return events.filter(Q(start_day__gte=now.date(), start_time__gte=now.time()) | Q(start_day__gte=now.date()))

    def penalized(self, user: User) -> int:
        today = datetime.now().date()
        return models.Enrollment.objects.filter(
            event__created_by=user,
            event__start_day__gte=today,
            event__start_day__lte=today + timedelta(days=4),
            status='ACCEPTED'
        ).values('event__price').annotate(
            count=Count('event'),
        )

    def rated_by_user(self, user: User, on='HOST') -> QuerySet:
        return models.Event.objects.filter(ratings__created_by=user, ratings__on=on)

    def nearby_events_distance(self, user, distance, latitude, longitude, **kwargs):
        filters = {key: val for key, val in kwargs.items() if val}
        events = self.base_search_events(user).filter(**filters)
        result = []

        if events:
            events_distances_oredered = self.common_method_distance_order(
                events, latitude, longitude)

            for event, eventdistance in events_distances_oredered.items():
                if eventdistance <= int(distance):
                    result.append(event.id)
                else:
                    break
        return models.Event.objects.filter(pk__in=result)

    def events_filter_search(self, user: User, **kwargs) -> QuerySet:
        events = self.base_search_events(user)
        filters = {key: val for key, val in kwargs.items() if val}
        return events.filter(**filters)

    def base_search_events(self, user: User) -> QuerySet:
        now = datetime.now()
        if user.is_authenticated:
            events = models.Event.objects.filter(
                ~Q(event_enrollments__created_by=user) & (Q(start_day__gte=now.date(), start_time__gte=now.time()) | Q(start_day__gte=now.date())))
        else:
            events = models.Event.objects.filter(Q(start_day__gte=now.date(
            ), start_time__gte=now.time()) | Q(start_day__gte=now.date()))
        return events

    def common_method_distance_order(self, events, latitude, longitude):
        gmaps = googlemaps.Client(key=settings.GOOGLE_API_KEY)
        events_distances = {}

        latitude_user = latitude
        longitude_user = longitude

        origins = [{"lat": latitude_user, "lng": longitude_user}]

        new_event_list = [events[i:i+20] for i in range(0, len(events), 20)]

        for event_list in new_event_list:
            destinations = ""

            for event in event_list:
                destinations = destinations + str(
                    event.location_number) + " " + event.location_street + ", " + event.location_city + "|"

            distancematrix = gmaps.distance_matrix(origins, destinations)

            for element, event in zip(distancematrix['rows'][0]['elements'], event_list):
                if element['status'] == 'OK':
                    events_distances[event] = element['distance']['value']

        events_distances_oredered = OrderedDict(
            sorted(events_distances.items(), key=itemgetter(1), reverse=False))

        return events_distances_oredered


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
            attendee_enrollments__event__pk=event_pk, attendee_enrollments__status='ACCEPTED')
        return event_attendees

    def event_enrolled(self, event: int) -> QuerySet:
        return User.objects.filter(Q(attendee_enrollments__event=event) & ~Q(attendee_enrollments__status='REJECTED'))

    def events_enrolleds(self, events) -> QuerySet:
        return User.objects.filter(Q(attendee_enrollments__event__in=events) & ~Q(attendee_enrollments__status='REJECTED'))

    def events_attendees(self, events) -> QuerySet:
        return User.objects.filter(attendee_enrollments__event__in=events, attendee_enrollments__status='ACCEPTED')

    def rated_on_event(self, event_pk: int) -> QuerySet:
        return User.objects.filter(reviewed_ratings__event=event_pk)

    def with_token(self, token: str) -> User:
        return User.objects.filter(profile__token=token).first()


class TransactionSelector:
    def users_on_events(self, users, events) -> QuerySet:
        return models.Transaction.objects.filter(created_by__in=users, event__in=events)

    def user_transactions(self, user: User) -> QuerySet:
        transaction_list = models.Transaction.objects.filter(
            created_by=user, is_paid_for=True)
        return transaction_list


class MessageSelector:
    def last_message(self) -> models.Message:
        return models.Message.objects.latest()
