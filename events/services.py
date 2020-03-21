from collections import OrderedDict
from datetime import datetime, time
from operator import itemgetter

import googlemaps
import pytz
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils.timezone import now

from . import models
from . import selectors

API_KEY = "AIzaSyBY0HRt8y_5IBwScjIUqFT6nXmNs2gvhhQ"
User = get_user_model()


class EnrollmentService():
    def count(enrollment_pk: int) -> int:
        count = models.Enrollment.objects.filter(pk=enrollment_pk).count()
        return count

    def create(event_pk: int, created_by: User):
        event = models.Event.objects.get(pk=event_pk)
        enrollment = models.Enrollment.objects.create(
            created_by=created_by, event=event)
        enrollment.save()

    def is_pending(enrollment_pk: int) -> bool:
        enrollment = models.Enrollment.objects.get(pk=enrollment_pk)
        return enrollment.status == 'PENDING'

    def host_can_update(host: User, enrollment_pk: int) -> bool:
        created_by = models.Enrollment.objects.get(
            pk=enrollment_pk).event.created_by
        return host == created_by

    def update(enrollment_pk: int, updated_by: User, status: str):
        enrollment = models.Enrollment.objects.get(pk=enrollment_pk)
        enrollment.status = status
        enrollment.updated_by = updated_by
        enrollment.save()

    def user_is_enrolled(event_pk: int, user: User) -> bool:
        return models.Enrollment.objects.filter(event=event_pk, created_by=user).exists()


class EventService():
    def count(event_pk: int) -> int:
        count = models.Event.objects.filter(pk=event_pk).count()
        return count

    def create(event: models.Event, created_by: User):
        event.created_by = created_by
        event.full_clean()
        event.save()

    def enroll(attendee: User, event_pk: int) -> models.Event:
        event = models.Event.objects.get(pk=event_pk)

        if attendee.attendee_events.filter(pk=event_pk).exists():
            raise PermissionDenied('Already enrolled')
        attendee.attendee_events.add(event)
        return event
    
    def can_create(user: User) -> bool:
        res = True

        if user.profile.bio is None or user.first_name is None or user.last_name is None:
            res = False

        return res

    @staticmethod
    def nearby_events_distance(distance):
        # events = Event.objects.filter(starts_at__date__gt=datetime.now()).order_by('-starts_at')
        events = models.Event.objects.all()

        # Comprobar que haya algun evento
        events_distances_oredered = common_method(events)

        result = []
        for event, eventdistance in events_distances_oredered.items():
            if eventdistance <= int(distance):
                result.append(event)
            else:
                break

        return result

    @staticmethod
    def nearby_events_ordered():
        # events = Event.objects.filter(starts_at__date__gt=datetime.now()).order_by('-starts_at')
        events = models.Event.objects.all()

        # Comprobar que haya algun evento
        events_distances_oredered = common_method(events)

        return list(events_distances_oredered.keys())

    @staticmethod
    def events_filter_ordered_by_distance(max_price, minimum_price, year, month, day):
        # events = Event.objects.filter(starts_at__date__gt=datetime.now()).order_by('-starts_at')
        # Validar que la fecha es futura
        # events = Event.objects.all()
        events = models.Event.objects.filter(price__gte=minimum_price, price__lte=max_price, start_day__year=year,
                                             starts_day__month=month, starts_day__day=day)

        # Comprobar que haya algun evento
        events_distances_oredered = common_method(events)

        return list(events_distances_oredered.keys())

    def update(event: models.Event, updated_by: User):
        event.updated_by = updated_by
        event.full_clean()
        event.save()

    def user_is_owner(host: User, event_pk: int):
        created_by = models.Event.objects.get(pk=event_pk).created_by
        return host == created_by


class ProfileService():
    def create(user: User, picture: str):
        profile = models.Profile.objects.create(user=user, picture=picture)
        profile.save()


class RatingService():
    def count(rating_pk: int) -> int:
        count = models.Rating.objects.filter(pk=rating_pk).count()
        return count

    def create(rating: models.Rating):
        rating.full_clean()
        rating.save()

    def is_valid_rating(rating: models.Rating, event: models.Event, user: User):
        rating.created_by = user
        valid = False
        now = datetime.now()
        now = pytz.utc.localize(now)
        # the event must have ended
        if event.start_day < now.date():

            rating_user_for_this_event = selectors.RatingSelector.exists_this_rating_for_this_user_and_event(
                rating.created_by, event, rating.reviewed)
            # the user cannot have already rated this event
            if not rating_user_for_this_event:

                enroll_reviewed = selectors.EnrollmentSelector.enrolled_for_this_event(
                    rating.reviewed, event)

                # the host can only rate their attendees for this event
                if rating.on == 'ATTENDEE' and enroll_reviewed:

                    valid = True
                # the attendee can only rate the event host
                elif rating.reviewed == event.created_by:
                    valid = True
        return valid

    def is_attendee_or_host(event: models.Event, rating: models.Rating):
        rol = rating.on
        if event.created_by == rating.created_by:
            rol = 'ATTENDEE'
        else:
            rol = 'HOST'
        return rol


# Metodos auxiliares
def common_method(events):
    gmaps = googlemaps.Client(key=API_KEY)

    geolocation = gmaps.geolocate()

    latitude_user = geolocation['location']['lat']
    longitude_user = geolocation['location']['lng']

    origins = [{"lat": latitude_user, "lng": longitude_user}]
    destinations = ""

    for event in events:
        destinations = destinations + str(
            event.location_number) + " " + event.location_street + ", " + event.location_city + "|"

    distancematrix = gmaps.distance_matrix(origins, destinations)
    events_distances = {}

    for element, event in zip(distancematrix['rows'][0]['elements'], events):
        if element['status'] == 'OK':
            events_distances[event] = element['distance']['value']

    events_distances_oredered = OrderedDict(
        sorted(events_distances.items(), key=itemgetter(1), reverse=False))

    return events_distances_oredered
