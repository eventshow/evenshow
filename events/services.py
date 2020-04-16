import googlemaps
import pytz
import stripe

from datetime import date, datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.db import transaction as db_transaction
from django.db.models import F, Subquery, OuterRef
from django.utils.timezone import now

from . import models
from . import selectors

User = get_user_model()


class EmailService:
    def send_email(self, subject: str, body: str, recipient_list: list):
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

    def create(self, event_pk: int, created_by: User) -> models.Enrollment:
        event = models.Event.objects.get(pk=event_pk)
        enrollment = models.Enrollment.objects.create(
            created_by=created_by, event=event)
        enrollment.save()
        return enrollment

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

    def locations(self):
        locations = models.Event.objects.values_list(
            'location_city', flat=True).order_by('location_city').distinct('location_city').exclude(location_city='No disponible')
        return locations

    def can_update(self, event_pk):
        event = models.Event.objects.get(pk=event_pk)

        return event.can_update


class ProfileService():
    def create(self, user: User, birthdate: date, points: int):
        profile = models.Profile.objects.create(
            user=user, birthdate=birthdate, eventpoints=points)
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
    def fee(self, amount_host: int) -> int:
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

        return int(round(res - amount_host, 2))

    def fee_discount(self, amount_host: int, attendee: User) -> int:
        res = 0
        const_stripe = settings.STRIPE_CONST_FEE
        var_stripe = settings.STRIPE_VARIABLE_FEE
        discount = attendee.profile.discount

        amount_company = 0

        if (amount_host >= 0) and amount_host <= 50:
            amount_company = 15-discount
        elif (amount_host > 50) and (amount_host <= 150):
            amount_company = (amount_host * 0.25)-discount
        elif (amount_host > 150) and (amount_host <= 300):
            amount_company = (amount_host * 0.2)-discount
        elif (amount_host > 300) and (amount_host <= 500):
            amount_company = (amount_host * 0.15)-discount
        elif (amount_host > 500):
            amount_company = (amount_host * 0.10)-discount

        if amount_company < 0:
            res = amount_host * var_stripe + const_stripe
        else:
            res = (amount_host + amount_company) * var_stripe + const_stripe
        return int(round(res - amount_host, 2))

    def charge_connect(self, amount: int, customer_id: int, application_fee_amount: int, host: User) -> None:
        stripe.Charge.create(
            amount=amount,
            currency='eur',
            customer=customer_id,
            description='A event payment',
            application_fee_amount=application_fee_amount,
            destination={
                'account': host.profile.stripe_user_id,
            }
        )

    def charge(self, amount: int, source: str) -> None:
        stripe.Charge.create(
            amount=amount,
            currency='eur',
            description='A event payment',
            source=source
        )

    def save_transaction(self, amount: int, fee: int, customer_id: int, event: models.Event, created_by: User, recipient: User, discount=0):
        models.Transaction.objects.create(amount=amount, fee=fee, created_by=created_by, recipient=recipient,
                                          customer_id=customer_id, event=event, is_paid_for=False, discount=discount)

    def get_or_create_customer(self, email: str, source: str) -> stripe.Customer:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        connected_customers = stripe.Customer.list()
        for customer in connected_customers:
            if customer.email == email:
                return customer
        return stripe.Customer.create(
            email=email,
            source=source
        )

    def is_customer(self, email: str) -> bool:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        connected_customers = stripe.Customer.list()
        for customer in connected_customers:
            if customer.email == email:
                return True

        return False


class UserService:
    def add_bonus(self, user: User, price):
        points = int(round((float(price) * 100 *
                            settings.EVENTPOINT_BONUS) / settings.EVENTPOINT_VALUE))
        user.profile.eventpoints += points
        user.profile.save()

    def add_eventpoints(self, token: str) -> int:
        points = 0
        user = selectors.UserSelector().with_token(token)
        if user:
            points = settings.EVENTPOINTS
            user.profile.eventpoints += points
            user.profile.save()
        return points

    def return_eventpoints(self, attendees, events):
        with db_transaction.atomic():
            if isinstance(attendees, User):
                attendees = [attendees]
            else:
                attendees = attendees.exclude(username='deleted')

            if isinstance(events, models.Event):
                events = [events]

            transactions = selectors.TransactionSelector().users_on_events(attendees, events)
            discounts = transactions.filter(
                discount__gt=0).values_list('created_by', 'discount')
            for pk, discount in discounts:
                returned = int(
                    round(discount/settings.EVENTPOINT_VALUE/settings.STRIPE_VARIABLE_FEE))
                models.Profile.objects.filter(user__pk=pk).update(
                    eventpoints=F('eventpoints')+returned)
            transactions.delete()

    def exist_user(self, user_id: int) -> bool:
        exist = models.User.objects.filter(id=user_id).exists()
        return exist


class MessageService:
    def last_message(self):
        message = None
        if models.Message.objects.all():
            message = selectors.MessageSelector().last_message()
        return message
