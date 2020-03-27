import googlemaps
import pytz

from collections import OrderedDict
from datetime import date, datetime, time
from operator import itemgetter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils.timezone import now

from . import models
from . import selectors
from .models import Event
from django.core.mail import send_mail

User = get_user_model()

class EmailService:
    def send_email(self, subject:str, body:str, recipient_list:list) -> None:
        send_mail(
           subject,
           body,
           settings.EMAIL_HOST_USER,
           recipient_list,
           fail_silently=False,
       )

class EnrollmentService:
    def count(self, enrollment_pk: int) -> int:
        count = models.Enrollment.objects.filter(pk=enrollment_pk).count()
        return count

    def create(self, event_pk: int, created_by: User):
        event = models.Event.objects.get(pk=event_pk)
        enrollment = models.Enrollment.objects.create(
            created_by=created_by, event=event)
        enrollment.save()

    def is_pending(self, enrollment_pk: int) -> bool:
        enrollment = models.Enrollment.objects.get(pk=enrollment_pk)
        return enrollment.status == 'PENDING'

    def host_can_update(self, host: User, enrollment_pk: int) -> bool:
        created_by = models.Enrollment.objects.get(
            pk=enrollment_pk).event.created_by
        return host == created_by

    def update(self, enrollment_pk: int, updated_by: User, status: str):
        enrollment = models.Enrollment.objects.get(pk=enrollment_pk)
        enrollment.status = status
        enrollment.updated_by = updated_by
        enrollment.save()

    def user_can_enroll(self, event_pk: int, user: User) -> bool:
        event = models.Event.objects.get(pk=event_pk)
        user_is_enrolled = self.user_is_enrolled(
            event_pk, user)
        user_is_old_enough = self.user_is_old_enough(event_pk, user)
        user_is_owner = EventService().user_is_owner(user, event_pk)
        return not user_is_enrolled and user_is_old_enough and not user_is_owner

    def user_is_enrolled(self, event_pk: int, user: User) -> bool:
        return models.Enrollment.objects.filter(event=event_pk, created_by=user).exists()

    def user_is_enrolled_and_accepted(self, event_pk: int, user: User, status='ACCEPTED') -> bool:
        return models.Enrollment.objects.filter(event=event_pk, created_by=user, status=status).exists()

    def user_is_old_enough(self, event_pk: int, user: User) -> bool:
        event = models.Event.objects.get(pk=event_pk)
        return event.min_age <= user.profile.age


class EventService():
    def count(self, event_pk: int) -> int:
        count = models.Event.objects.filter(pk=event_pk).count()
        return count

    def create(self, event: models.Event, created_by: User):
        event.created_by = created_by
        event.full_clean()
        event.save()

    def enroll(self, attendee: User, event_pk: int) -> models.Event:
        event = models.Event.objects.get(pk=event_pk)

        if attendee.attendee_events.filter(pk=event_pk).exists():
            raise PermissionDenied('Already enrolled')
        attendee.attendee_events.add(event)
        return event

    def can_create(self, user: User) -> bool:
        res = True

        if user.profile.bio is None or user.first_name is None or user.last_name is None:
            res = False

        return res

    def nearby_events_distance(self, self_view, distance, latitude, longitude):
        events = Event.objects.filter(start_day__gte=date.today())

        events_cleaned = []
        if self_view.request.user.is_authenticated:
            for event in events:
                if self_view.request.user not in selectors.UserSelector().event_attendees(
                        event.pk) and event.has_started is False:
                    events_cleaned.append(event)
        else:
            for event in events:
                if event.has_started is False:
                    events_cleaned.append(event)

        result = []

        if events_cleaned:
            events_distances_oredered = self.common_method_distance_order(
                events_cleaned, latitude, longitude)

            for event, eventdistance in events_distances_oredered.items():
                if eventdistance <= int(distance):
                    result.append(event)
                else:
                    break

        return result

    def events_filter_home(self, self_view, location, event_date, start_hour):
        if location and event_date and start_hour:
            events = selectors.EventSelector().location_date_start_hour(
                location, event_date, start_hour)
        elif location and event_date:
            events = selectors.EventSelector().location_date(
                location, event_date)
        elif location and start_hour:
            events = selectors.EventSelector().location_start_hour(
                location, start_hour)
        elif event_date and start_hour:
            events = selectors.EventSelector().date_start_hour(
                event_date, start_hour)
        elif location:
            events = selectors.EventSelector().location(location)
        elif event_date:
            events = selectors.EventSelector().date(event_date)
        elif start_hour:
            events = selectors.EventSelector().start_hour(start_hour)
        else:
            events = Event.objects.filter(start_day__gte=date.today())

        results = []
        if self_view.request.user.is_authenticated:
            for event in events:
                if self_view.request.user not in selectors.UserSelector().event_attendees(
                        event.pk) and event.has_started is False:
                    results.append(event)
        else:
            for event in events:
                if event.has_started is False:
                    results.append(event)

        return results

    def common_method_distance_order(self, events, latitude, longitude):
        gmaps = googlemaps.Client(key=settings.GOOGLE_API_KEY)

        latitude_user = latitude
        longitude_user = longitude

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

    def update(self, event: models.Event, updated_by: User):
        event.updated_by = updated_by
        event.full_clean()
        event.save()

    def user_is_owner(self, host: User, event_pk: int) -> bool:
        return models.Event.objects.filter(created_by=host, pk=event_pk).exists()

    def has_finished(self, event_pk: int):
        event = models.Event.objects.get(pk=event_pk)
        return event.has_finished

    def exist_event(self, event_id: int) -> bool:
        exist = models.Event.objects.filter(id=event_id).exists()
        return exist


class ProfileService():
    def create(self, user: User, birthdate: date):
        profile = models.Profile.objects.create(user=user, birthdate=birthdate)
        profile.save()


class RatingService:
    def count(self, rating_pk: int) -> int:
        count = models.Rating.objects.filter(pk=rating_pk).count()
        return count

    def create(self, rating: models.Rating):
        rating.full_clean()
        rating.save()

    def is_valid_rating(self, rating: models.Rating, event: models.Event, user: User):
        rating.created_by = user
        valid = False
        now = datetime.now()
        now = pytz.utc.localize(now)
        # the event must have ended
        if event.has_finished:
            rating_user_for_this_event = selectors.RatingSelector().exists_this_rating_for_this_user_and_event(
                rating.created_by, event, rating.reviewed)
            # the user cannot have already rated this event
            if not rating_user_for_this_event:

                enroll_reviewed = event in selectors.EventSelector().enrolled(rating.reviewed)

                # the host can only rate their attendees for this event
                if rating.on == 'ATTENDEE' and enroll_reviewed:

                    valid = True
                # the attendee can only rate the event host
                elif rating.reviewed == event.created_by:

                    valid = True
        return valid

    def is_attendee_or_host(self, event: models.Event, rating: models.Rating):
        rol = rating.on
        if event.created_by == rating.created_by:
            rol = 'ATTENDEE'
        else:
            rol = 'HOST'
        return rol


class PaymentService():

    def application_fee_amount(self, amount_host: int) -> int:

        res = 0
        const_stripe = 25
        var_stripe = 1.029

        if (amount_host >= 0) and amount_host <= 50:
            res = (amount_host + 15) * var_stripe + const_stripe
        elif (amount_host > 50) and (amount_host <= 150):
            res = (amount_host * 1.25) * var_stripe + const_stripe
        elif (amount_host > 150) and (amount_host <= 300):
            res = (amount_host * 1.2) * var_stripe + const_stripe
        elif (amount_host > 300) and (amount_host <= 500):
            res = (amount_host * 1.15) * var_stripe + const_stripe
        elif (amount_host > 500):
            res = (amount_host * 1.10) * var_stripe + const_stripe

        return round(res - amount_host)


class UserService:
    def exist_user(self, user_id: int) -> bool:
        exist = models.User.objects.filter(id=user_id).exists()
        return exist
