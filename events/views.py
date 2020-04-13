import stripe
import requests
import urllib

from django.db.models import Count, Sum
from datetime import date, datetime

from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required

from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views import generic
from django.views.defaults import page_not_found
from django.views.generic.list import MultipleObjectMixin
from xhtml2pdf import pisa

from . import forms
from . import models
from . import selectors
from . import services
from django.utils.datastructures import MultiValueDictKeyError

stripe.api_key = settings.STRIPE_SECRET_KEY

EVENT_SUCCESS_URL = reverse_lazy('hosted_events')
User = get_user_model()


def handler_404(request, exception):
    return page_not_found(request, exception, template_name='404.html')


def not_impl(request):
    return render(request, 'not_impl.html', {'STATIC_URL': settings.STATIC_URL})


class HomeView(generic.FormView):
    form_class = forms.SearchHomeForm
    template_name = 'home.html'

    def render_to_response(self, context, **response_kwargs):
        context['message'] = services.MessageService().last_message()
        context['locations'] = services.EventService().locations()
        response_kwargs.setdefault('content_type', self.content_type)
        return self.response_class(
            request=self.request,
            template=self.get_template_names(),
            context=context,
            using=self.template_engine,
            **response_kwargs
        )

    def form_valid(self, form):
        data = form.cleaned_data
        request = self.request.POST.copy()

        kwargs = {}
        kwargs['date'] = data.pop('date', None) or None
        kwargs['start_hour'] = data.pop('start_hour', None) or None

        nearby = request.get('nearby', None) or None
        latitude = data.get('latitude', None) or None
        longitude = data.get('longitude', None) or None

        if nearby and not(latitude and longitude):
            context = self.get_context_data(form=form)
            context['no_geolocation'] = 'No se ha podido determinar tu ubicación'
            return self.render_to_response(context)
        elif nearby:
            self.request.session['latitude'] = float(latitude)
            self.request.session['longitude'] = float(longitude)
            del request['location']
        elif self.request.session.get('latitude') or self.request.session.get('longitude'):
            del self.request.session['latitude']
            del self.request.session['longitude']
            kwargs['location'] = data.pop('location', None) or None
        else:
            kwargs['location'] = data.pop('location', None) or None

        if self.request.session.get('form_values'):
            del self.request.session['form_values']

        self.request.session['form_values'] = request
        kwargs = {key: val for key, val in kwargs.items() if val}
        return redirect(reverse('list_event_filter', kwargs=kwargs))


@method_decorator(login_required, name='dispatch')
class AttendeeListView(generic.ListView):
    model = User
    template_name = 'attendee/list.html'
    paginate_by = 5

    def get(self, request, *args, **kwargs):
        event_pk = kwargs.get('pk')
        if services.EventService().count(event_pk) and services.EventService().user_is_owner(request.user, event_pk):
            return super(AttendeeListView, self).get(self, request, *args, **kwargs)
        else:
            return redirect('/')

    def get_context_data(self, **kwargs):
        event_pk = self.kwargs.get('pk')
        event = models.Event.objects.get(pk=event_pk)
        context = super(AttendeeListView, self).get_context_data(**kwargs)
        context['event_has_finished'] = event.has_finished
        context['event_has_started'] = event.has_started
        context['event_pk'] = event_pk
        context['event_title'] = event.title
        context['rated_attendees'] = selectors.UserSelector(
        ).rated_on_event(event_pk)
        return context

    def get_queryset(self):
        queryset = selectors.UserSelector().event_attendees(
            self.kwargs.get('pk')).order_by('username')
        return queryset


class AttendeePaymentView(generic.View):

    def post(self, request, *args, **kwargs):
        if services.EventService().count(kwargs.get('pk')):
            pk = self.kwargs.get('pk')
            event = models.Event.objects.get(pk=pk)
            if self.request.user.profile.stripe_access_token is None and self.request.user.profile.stripe_user_id is None:
                return redirect('authorize')
            else:
                if event.has_finished:

                    attende_list = selectors.UserSelector().event_attendees(pk)

                    for attendee in attende_list:

                        transaction = models.Transaction.objects.filter(
                            created_by=attendee, event=event).first()

                        if transaction:

                            is_paid_for = transaction.is_paid_for

                            if not is_paid_for:

                                try:
                                    print(transaction.discount)
                                    fee = 0
                                    if transaction.discount:

                                        fee = services.PaymentService().fee_discount(
                                            transaction.amount, attendee, False)
                                    else:
                                        fee = services.PaymentService().fee(transaction.amount)

                                    attendee_amount = fee + transaction.amount


                                    services.PaymentService().charge_connect(
                                        attendee_amount, transaction.customer_id, fee, transaction.recipient)

                                    transaction.is_paid_for = True
                                    transaction.save()

                                    if not transaction.discount:
                                        print('----------------')
                                        services.UserService().add_bonus(transaction.created_by, transaction.amount)

                                except stripe.error.StripeError:
                                    redirect('payment_error')

                            else:

                                return redirect('/')

                    return redirect('hosted_events')

                else:
                    return redirect('/')
        else:
            return redirect('/')


class EventDetailView(generic.DetailView, MultipleObjectMixin):
    model = models.Event
    template_name = 'event/detail.html'
    paginate_by = 3

    def get(self, request, *args, **kwargs):
        if services.EventService().count(kwargs.get('pk')):
            return super().get(self, request, *args, **kwargs)
        else:
            return redirect('/')

    def get_context_data(self, **kwargs):
        user = self.request.user
        event = kwargs.get('object')
        object_list = selectors.RatingSelector().on_user(
            event.created_by)
        context = super(EventDetailView, self).get_context_data(
            object_list=object_list, **kwargs)
        duration = event.duration

        event_is_full = selectors.UserSelector().event_attendees(
            event.pk).count() >= event.capacity
        user_can_enroll = True

        if user.is_authenticated:
            context['user_is_enrolled'] = services.EnrollmentService(
            ).user_is_enrolled(event.pk, user)
            context['user_is_old_enough'] = services.EnrollmentService(
            ).user_is_old_enough(event.pk, user)
            context['user_is_owner'] = services.EventService(
            ).user_is_owner(user, event.pk)

            context['have_creditcard'] = services.PaymentService(
            ).is_customer(user.email)

            user_can_enroll = not context.get('user_is_enrolled') and context.get(
                'user_is_old_enough') and not context.get('user_is_owner')

            context['price_discount'] = (services.PaymentService().fee_discount(
                float(event.price*100), user, True) + event.price*100)/100
            context['price_discount_cent'] = (services.PaymentService().fee_discount(
                float(event.price*100), user, True) + event.price*100)
            context['price_all'] = (services.PaymentService().fee(
                float(event.price*100)) + event.price*100)/100
            context['price_all_cent'] = (services.PaymentService().fee(
                float(event.price*100)) + event.price*100)

        hours, minutes = divmod(duration, 60)
        context['duration'] = '{0}h {1}min'.format(hours, minutes)
        context['gmaps_key'] = settings.GOOGLE_API_KEY
        context['stripe_key'] = settings.STRIPE_PUBLISHABLE_KEY
        context['event_is_full'] = event_is_full
        context['points'] = user.profile.eventpoints
        context['attendees'] = selectors.EnrollmentSelector().on_event(
            event.pk, 'ACCEPTED').count()
        context['event_price'] = float(event.price) + services.PaymentService().fee(
            float(event.price)*100) / 100
        context['user_can_enroll'] = not event_is_full and user_can_enroll
        context['commission'] = services.PaymentService().fee(float(event.price)*100) / 100

        return context


@method_decorator(login_required, name='dispatch')
class EventCreateView(generic.CreateView):
    model = models.Event
    form_class = forms.EventForm
    success_url = EVENT_SUCCESS_URL
    template_name = 'event/update.html'

    def get(self, request, *args, **kwargs):
        if services.EventService().can_create(self.request.user):
            return super().get(request, *args, **kwargs)
        else:
            return redirect('/')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = models.Category.objects.all()

        return context

    def form_valid(self, form):
        event = form.save(commit=False)
        services.EventService().create(event, self.request.user)
        return super(EventCreateView, self).form_valid(form)


@method_decorator(login_required, name='dispatch')
class EventDeleteView(generic.DeleteView):
    template_name = 'event/event_confirm_delete.html'
    model = models.Event
    success_url = EVENT_SUCCESS_URL

    def get_context_data(self, **kwargs):

        context = super(EventDeleteView, self).get_context_data(**kwargs)
        context['stripe_key'] = settings.STRIPE_PUBLISHABLE_KEY

        event_pk = self.kwargs.get('pk')
        if services.EventService().count(event_pk):
            event = models.Event.objects.get(pk=event_pk)

            attendees = selectors.UserSelector().event_attendees(event_pk).count()
            amount_host = services.PaymentService().fee(round(event.price*100))
            context['penalty'] = (amount_host*attendees)
            context['attendees_count'] = attendees
            print(context['attendees_count'])

        return context

    def delete(self, request, *args, **kwargs):
        host = request.user
        event_pk = self.kwargs.get('pk')
        if services.EventService().count(event_pk) and services.EventService().user_is_owner(host, kwargs.get('pk')):
            self.object = self.get_object()
            event = models.Event.objects.get(pk=event_pk)

            if not event.can_delete:
                penalty(event, request.POST.get('stripeToken'))

            subject = 'Evento cancelado'
            body = 'El evento ' + event.title + ' en el que estás inscrito ha sido cancelado'
            recipient_list_queryset = selectors.UserSelector().event_attendees(event_pk)
            recipient_list = list(
                recipient_list_queryset.values_list('email', flat=True))
            services.EmailService().send_email(subject, body, recipient_list)
            self.object.delete()
            return redirect('hosted_events')
        else:
            return redirect('/')

    def get(self, request, *args, **kwargs):
        host = request.user
        event_pk = self.kwargs.get('pk')
        if services.EventService().count(event_pk) and services.EventService().user_is_owner(host, self.kwargs.get(
                'pk')) and not services.EventService().has_finished(event_pk):
            return super().get(request, *args, **kwargs)
        else:
            return redirect('/')


@method_decorator(login_required, name='dispatch')
class EventHostedListView(generic.ListView):
    model = models.Event
    template_name = 'event/list.html'
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super(EventHostedListView, self).get_context_data(**kwargs)
        context['role'] = 'anfitrión'
        return context

    def get_queryset(self):
        queryset = selectors.EventSelector().hosted(
            self.request.user).order_by('start_day')
        return queryset


@method_decorator(login_required, name='dispatch')
class EventEnrolledListView(generic.ListView):
    model = models.Enrollment
    template_name = 'event/list.html'
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super(EventEnrolledListView, self).get_context_data(**kwargs)
        context['user_rated_events'] = selectors.EventSelector().rated_by_user(
            self.request.user)
        context['role'] = 'huésped'
        return context

    def get_queryset(self):
        queryset = selectors.EnrollmentSelector().created_by(
            self.request.user).order_by('event__start_day')
        return queryset


@method_decorator(login_required, name='dispatch')
class EventUpdateView(generic.UpdateView):
    model = models.Event
    form_class = forms.EventForm
    success_url = EVENT_SUCCESS_URL
    template_name = 'event/update.html'

    def form_valid(self, form):
        host = self.request.user
        event_pk = self.kwargs.get('pk')
        if services.EventService().count(event_pk) and services.EventService().user_is_owner(host, event_pk):
            event = form.save(commit=False)
            event_db = models.Event.objects.get(pk=event_pk)

            attende_list = selectors.UserSelector().event_attendees(event_pk)

            subject = 'Evento actualizado'
            body = 'El evento ' + event_db.title + \
                'en el que estás inscrito ha sido actualizado'
            recipient_list_queryset = selectors.UserSelector().event_attendees(event_pk)
            recipient_list = list(
                recipient_list_queryset.values_list('email', flat=True))
            services.EmailService().send_email(subject, body, recipient_list)
            services.EventService().update(event, host)
            return super(EventUpdateView, self).form_valid(form)

        else:
            return redirect('events')

    def get(self, request, *args, **kwargs):
        host = request.user
        event_pk = self.kwargs.get('pk')

        if services.EventService().count(event_pk) and services.EventService().user_is_owner(host, kwargs.get(
                'pk')) and not services.EventService().has_finished(event_pk) and services.EventService().can_update(event_pk):

            return super().get(request, *args, **kwargs)
        else:
            return redirect('/')


class EventFilterFormView(generic.FormView):
    form_class = forms.SearchFilterForm
    template_name = 'event/list_search.html'

    def form_valid(self, form):
        data = form.cleaned_data

        kwargs = {}
        kwargs['date'] = data.pop('date', None) or None
        kwargs['location'] = data.pop('location', None) or None
        kwargs['start_hour'] = data.pop('start_hour', None) or None
        kwargs['min_price'] = data.pop('min_price', None) or None
        kwargs['max_price'] = data.pop('max_price', None) or None
        kwargs['category'] = self.request.POST.get('category', None) or None
        self.request.session['form_values'] = self.request.POST

        kwargs = {key: val for key, val in kwargs.items() if val}

        if self.request.session.get('latitude'):
            if not bool(kwargs) or (bool(kwargs) and kwargs.get('location')):
                del self.request.session['latitude']
                del self.request.session['longitude']

        return redirect(reverse('list_event_filter', kwargs=kwargs))

    def form_invalid(self, form):
        self.request.session['form_values'] = self.request.POST
        return redirect('list_event_filter')


class EventFilterListView(generic.ListView):
    model = models.Event
    template_name = 'event/list_search.html'
    paginate_by = 12
    form_class = forms.SearchFilterForm

    def get_context_data(self, **kwargs):
        context = super(EventFilterListView,
                        self).get_context_data(**kwargs)
        context['locations'] = services.EventService().locations()
        context['location'] = self.kwargs.get('location_city__icontains', None)
        context['category'] = models.Category.objects.filter(
            pk=self.kwargs.get('category')).values_list('name', flat=True).first()
        context['form'] = self.form_class(
            self.request.session.get('form_values'))
        context['categories'] = context.get('paginator').object_list.values(
            'category__name', 'category').annotate(total=Count('category')).order_by('total')
        return context

    def get_queryset(self):
        self.kwargs['start_day'] = self.kwargs.pop('date', None) or None
        self.kwargs['location_city__icontains'] = self.kwargs.pop(
            'location', None) or None
        self.kwargs['start_time__gte'] = self.kwargs.pop(
            'start_hour', None) or None
        self.kwargs['price__gte'] = self.kwargs.pop(
            'min_price', None) or None
        self.kwargs['price__lte'] = self.kwargs.pop(
            'max_price', None) or None
        self.kwargs['category'] = self.kwargs.pop('category', None) or None

        latitude = self.request.session.get('latitude')
        longitude = self.request.session.get('longitude')

        if not (latitude and longitude):
            queryset = selectors.EventSelector().events_filter_search(
                self.request.user, **self.kwargs).order_by('start_day')
        else:
            queryset = selectors.EventSelector().nearby_events_distance(
                self.request.user, 50000, self.request.session.get('latitude'), self.request.session.get('longitude'), **self.kwargs)

        return queryset


@method_decorator(login_required, name='dispatch')
class EnrollmentCreateView(generic.View):
    model = models.Enrollment

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_pk = kwargs.get('pk')
        event = models.Event.object.get(pk=event_pk)
        context['event_title'] = event.title

    def post(self, request, *args, **kwargs):
        attendee = self.request.user
        event_pk = kwargs.get('pk')
        event = models.Event.objects.get(pk=event_pk)
        event_exists = services.EventService().count(event_pk)
        event_is_full = selectors.UserSelector().event_attendees(
            event_pk).count() >= event.capacity
        event_has_started = event.has_started
        user_can_enroll = services.EnrollmentService().user_can_enroll(
            event_pk, attendee)

        context = {'event_title': models.Event.objects.get(pk=event_pk)}

        if event_exists and user_can_enroll and not event_is_full and not event_has_started:
            enrollment = services.EnrollmentService().create(event_pk, attendee)
            
            event = models.Event.objects.get(pk=event_pk)
            if not services.PaymentService().is_customer(attendee.email):
                customer = services.PaymentService().get_or_create_customer(
                    request.user.email, request.POST['stripeToken'])
            else:
                customer = services.PaymentService().get_or_create_customer(request.user.email, None)
            services.PaymentService().save_transaction(
                int(event.price*100), customer.id, event, attendee, event.created_by, False)

            subject = 'Nueva inscripción a {0}'.format(event.title)
            body = 'El usuario {0} se ha inscrito a tu evento {1} en Eventshow'.format(
                enrollment.created_by.username, event.title)
            recipient = event.created_by.email

            services.EmailService().send_email(subject, body, [recipient])

            return render(request, 'enrollment/thanks.html', context)
        else:
            return redirect('/')


@method_decorator(login_required, name='dispatch')
class EnrollmentCreateDiscountView(generic.View):
    model = models.Enrollment

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_pk = kwargs.get('pk')
        event = models.Event.object.get(pk=event_pk)
        context['event_title'] = event.title

    def post(self, request, *args, **kwargs):
        attendee = self.request.user
        event_pk = kwargs.get('pk')
        event = models.Event.objects.get(pk=event_pk)
        event_exists = services.EventService().count(event_pk)
        event_is_full = selectors.UserSelector().event_attendees(
            event_pk).count() >= event.capacity
        event_has_started = event.has_started
        user_can_enroll = services.EnrollmentService().user_can_enroll(
            event_pk, attendee)

        context = {'event_title': models.Event.objects.get(pk=event_pk)}

        if event_exists and user_can_enroll and not event_is_full and not event_has_started:
            enrollment = services.EnrollmentService().create(event_pk, attendee)

            event = models.Event.objects.get(pk=event_pk)
            if not services.PaymentService().is_customer(attendee.email):
                customer = services.PaymentService().get_or_create_customer(
                    request.user.email, request.POST['stripeToken'])
            else:
                customer = services.PaymentService().get_or_create_customer(request.user.email, None)

            price = float(event.price) + services.PaymentService().fee(
                float(event.price)*100) / 100
            services.PaymentService().save_transaction(int(event.price*100), customer.id, event, attendee, event.created_by, True)


            subject = 'Nueva inscripción a {0}'.format(event.title)
            body = 'El usuario {0} se ha inscrito a tu evento {1} en Eventshow'.format(
                enrollment.created_by.username, event.title)
            recipient = event.created_by.email

            services.EmailService().send_email(subject, body, [recipient])

            return render(request, 'enrollment/thanks.html', context)
        else:
            return redirect('/')


class EnrollmentDeleteView(generic.View):
    model = models.Enrollment
    template_name = 'enrollment/list.html'

    def post(self, request, *args, **kwargs):
        enrollment = models.Enrollment.objects.filter(
            pk=kwargs.get('pk')).first()
        event = enrollment.event
        if enrollment and not event.has_started:
            user = self.request.user
            if (enrollment.is_accepted and (event.start_day - date.today()).days > 3) or not enrollment.is_accepted:
                selectors.TransactionSelector().user_on_event(user, event).delete()
            enrollment.delete()

            subject = 'Asistencia a {0} cancelada'.format(event.title)
            body = 'El usuario {0} ha cancelado su asistencia a tu evento {1} en Eventshow'.format(
                user.username, event.title)
            recipient = event.created_by.email
            services.EmailService().send_email(subject, body, [recipient])

            return redirect('enrolled_events')
        else:
            return redirect('/')


@method_decorator(login_required, name='dispatch')
class EnrollmentListView(generic.ListView):
    model = models.Enrollment
    template_name = 'enrollment/list.html'

    def get(self, request, *args, **kwargs):
        host = request.user
        event_pk = kwargs.get('pk')

        if services.EventService().count(event_pk) and services.EventService().user_is_owner(host, event_pk):
            return super(EnrollmentListView, self).get(request, *args, **kwargs)
        else:
            return redirect('/')

    def get_queryset(self):
        return selectors.EnrollmentSelector().on_event(self.kwargs.get('pk'), 'PENDING')


@method_decorator(login_required, name='dispatch')
class EnrollmentUpdateView(generic.View):
    model = models.Enrollment
    template_name = 'enrollment/list.html'

    def post(self, request, *args, **kwargs):
        host = self.request.user
        enrollment_pk = kwargs.get('pk')
        status = request.POST.get('status')

        if services.EnrollmentService().count(enrollment_pk) and self.updatable(host) and (
                status == 'ACCEPTED' or status == 'REJECTED'):
            services.EnrollmentService().update(
                enrollment_pk, host, status)
            event = models.Enrollment.objects.get(pk=enrollment_pk).event

            if status == 'ACCEPTED':
                status_txt = 'aceptada'
            else:
                status_txt = 'rechazada'

            subject = 'Solicitud para {0} {1}'.format(event.title, status_txt)
            body = 'Tu solicitud en Eventshow para el evento {0} ha sido {1}'.format(
                event.title, status_txt)
            recipient = models.Enrollment.objects.get(
                pk=enrollment_pk).created_by

            services.EmailService().send_email(
                subject, body, [recipient.email])

            return redirect('list_enrollments', event.pk)
        else:
            return redirect('/')

    def updatable(self, host):
        enrollment_pk = self.kwargs.get('pk')
        event_has_started = models.Enrollment.objects.get(
            pk=enrollment_pk).event.has_started
        return services.EnrollmentService().host_can_update(host,
                                                            enrollment_pk) and services.EnrollmentService().is_pending(
            enrollment_pk) and not event_has_started


@method_decorator(login_required, name='dispatch')
class PasswordUpdateView(generic.UpdateView):
    template_name = 'profile/update_password.html'
    model = User
    form_class = forms.PasswordUpdateForm
    success_url = reverse_lazy('detail_profile')

    def get_context_data(self, **kwargs):
        context = super(PasswordUpdateView, self).get_context_data(**kwargs)
        context['form'] = self.form_class(user=self.object)
        return context

    def get_object(self):
        return self.request.user


@method_decorator(login_required, name='dispatch')
class RateHostView(generic.CreateView):
    template_name = 'rating/rating.html'
    model = models.Rating
    form_class = forms.RatingForm
    success_url = '/events/enrolled'

    def get(self, request, *args, **kwargs):
        created_by = request.user
        event_exist = services.EventService().exist_event(self.kwargs.get('event_pk'))
        if (not event_exist):
            return redirect('home')
        else:
            event = models.Event.objects.get(pk=self.kwargs.get('event_pk'))
            exist_already_rating = selectors.RatingSelector().exists_this_rating_for_this_user_and_event(created_by,
                                                                                                         event,
                                                                                                         event.created_by)

            is_enrolled_for_this_event = services.EnrollmentService().user_is_enrolled_and_accepted(event.id,
                                                                                                    created_by)
            host = event.created_by
            auto_rating = self.request.user.id == host.id

            if (not exist_already_rating) and is_enrolled_for_this_event and event.has_finished and (not auto_rating) and host.username != 'deleted':
                return super().get(self, request, args, *kwargs)
            else:
                return redirect('home')

    def get_context_data(self, **kwargs):
        context = super(RateHostView, self).get_context_data(**kwargs)
        user = selectors.UserSelector(
        ).event_host(self.kwargs.get('event_pk'))
        context['event_pk'] = self.kwargs.get('event_pk')
        context['user_img'] = models.Profile.objects.get(
            user_id=user.id).picture
        context['host_name'] = selectors.UserSelector(
        ).event_host(self.kwargs.get('event_pk'))
        context['event_title'] = models.Event.objects.get(
            id=self.kwargs.get('event_pk')).title

        return context

    def form_valid(self, form):

        rating = form.save(commit=False)
        event = models.Event.objects.get(id=self.kwargs.get('event_pk'))
        host = selectors.UserSelector().event_host(self.kwargs.get('event_pk'))
        created_by = self.request.user

        rating.created_by = created_by
        rating.reviewed = host
        rating.event = event
        rating.on = 'HOST'
        if services.RatingService().is_valid_rating(rating, event, created_by) and host.username != 'deleted':
            services.RatingService().create(rating)
            return super().form_valid(form)
        else:
            return redirect('home')


@method_decorator(login_required, name='dispatch')
class RateAttendeeView(generic.CreateView):
    template_name = 'rating/rating.html'
    model = models.Rating
    form_class = forms.RatingForm

    def get(self, request, *args, **kwargs):
        created_by = request.user
        event_exist = services.EventService().exist_event(self.kwargs.get('event_pk'))
        attendee_exist = services.UserService().exist_user(self.kwargs.get('attendee_pk'))
        if not (event_exist and attendee_exist):
            return redirect('home')
        else:
            event = models.Event.objects.get(pk=self.kwargs.get('event_pk'))
            attendee_id = self.kwargs.get('attendee_pk')
            attendee = models.User.objects.get(id=attendee_id)
            exist_already_rating = selectors.RatingSelector().exists_this_rating_for_this_user_and_event(created_by,
                                                                                                         event,
                                                                                                         attendee_id)
            is_owner_of_this_event = services.EventService().user_is_owner(
                created_by, event.id)
            attendee_enrolled_for_this_event = services.EnrollmentService().user_is_enrolled_and_accepted(event.id,
                                                                                                          attendee)
            auto_rating = self.request.user.id == attendee.id
            if (
                    not exist_already_rating) and is_owner_of_this_event and attendee_enrolled_for_this_event and event.has_finished and (
                    not auto_rating) and attendee.username != 'deleted':
                return super().get(self, request, args, *kwargs)
            else:
                return redirect('home')

    def get_context_data(self, **kwargs):
        context = super(RateAttendeeView, self).get_context_data(**kwargs)
        context['event_pk'] = self.kwargs.get('event_pk')
        context['img_user'] = models.Profile.objects.get(
            user_id=self.kwargs.get('attendee_pk')).picture
        context['attendee_pk'] = self.kwargs.get('attendee_pk')
        context['attendee_name'] = models.User.objects.get(
            id=self.kwargs.get('attendee_pk')).username
        context['event_title'] = models.Event.objects.get(
            id=self.kwargs.get('event_pk')).title

        return context

    def get_success_url(self):
        return reverse_lazy('list_attendees', kwargs={'pk': self.kwargs.get('event_pk')})

    def form_valid(self, form):
        rating = form.save(commit=False)

        event = models.Event.objects.get(id=self.kwargs.get('event_pk'))
        host = selectors.UserSelector().event_host(self.kwargs.get('event_pk'))
        created_by = self.request.user

        rating.created_by = created_by

        reviewed = models.User.objects.get(id=self.kwargs.get('attendee_pk'))
        rating.reviewed = reviewed
        rating.event = event
        rating.on = 'ATTENDEE'

        if services.RatingService().is_valid_rating(rating, event, created_by) and reviewed.username != 'deleted':
            services.RatingService().create(rating)
            return super().form_valid(form)
        else:
            return redirect('home')


class SignUpView(generic.CreateView):
    form_class = forms.RegistrationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        user = form.save()
        birthdate = form.cleaned_data.get('birthdate')
        friend_token = form.cleaned_data.get('friend_token')
        points = services.UserService().add_eventpoints(friend_token)
        services.ProfileService().create(user, birthdate, points)
        login(self.request, user, backend=settings.AUTHENTICATION_BACKENDS[1])
        return super(SignUpView, self).form_valid(form)


@method_decorator(login_required, name='dispatch')
class StripeAuthorizeCallbackView(generic.View):

    def get(self, request):
        code = request.GET.get('code')
        if code:
            data = {
                'client_secret': settings.STRIPE_SECRET_KEY,
                'grant_type': 'authorization_code',
                'client_id': settings.STRIPE_CONNECT_CLIENT_ID,
                'code': code
            }
            url = 'https://connect.stripe.com/oauth/token'
            resp = requests.post(url, params=data)

            stripe_user_id = resp.json()['stripe_user_id']
            stripe_access_token = resp.json()['access_token']
            usuario = request.session['usuario']
            user = User.objects.filter(pk=usuario).first()

            profile = user.profile
            profile.stripe_access_token = stripe_access_token
            profile.stripe_user_id = stripe_user_id
            profile.save()
            user.save()
        url = reverse('hosted_events')
        response = redirect(url)
        return response


@method_decorator(login_required, name='dispatch')
class StripeAuthorizeView(generic.View):

    def get(self, request):
        if not self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login'))
        request.session['usuario'] = request.user.id
        url = 'https://connect.stripe.com/oauth/authorize'
        params = {
            'response_type': 'code',
            'scope': 'read_write',
            'client_id': settings.STRIPE_CONNECT_CLIENT_ID,
            'redirect_uri': settings.STRIPE_REQUEST_URI
        }
        url = f'{url}?{urllib.parse.urlencode(params)}'
        request.session.modified = True
        return redirect(url)


@method_decorator(login_required, name='dispatch')
class TransactionListView(generic.ListView):
    model = models.Transaction
    template_name = 'profile/receipts.html'
    paginate_by = 5

    def get_queryset(self):
        queryset = selectors.TransactionSelector().my_transaction(self.request.user)
        return queryset


@method_decorator(login_required, name='dispatch')
class UserDeleteView(generic.DeleteView):
    template_name = 'profile/user_confirm_delete.html'
    model = User

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        try:
            if self.price_sum:
                services.PaymentService().charge(
                    round(self.fee)*self.attendee_sum,
                    request.POST.get('stripeToken')
                )
            user.delete()
            return redirect('home')
        except stripe.error.StripeError:
            return redirect('payment_error')

    def dispatch(self, request, *args, **kwargs):
        self.penalized_events = self.get_penalized_events()
        self.is_penalized = self.penalized_events.count()
        if self.is_penalized:
            aux = self.penalized_events.aggregate(
                Sum('event__price'), Sum('count'))
            self.price_sum = float(aux.get('event__price__sum', 0) or 0)*100
            self.attendee_sum = aux.get('count__sum', 0) or 0
            self.fee = services.PaymentService().fee(self.price_sum)
        return super(UserDeleteView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserDeleteView, self).get_context_data(**kwargs)

        context['penalized'] = self.is_penalized
        if self.is_penalized:
            context['penalty'] = self.fee * self.attendee_sum
            context['stripe_key'] = settings.STRIPE_PUBLISHABLE_KEY
        return context

    def get_object(self):
        return self.request.user

    def get_penalized_events(self):
        return selectors.EventSelector().penalized(self.get_object())


@method_decorator(login_required, name='dispatch')
class UserUpdateView(generic.UpdateView):
    template_name = 'profile/update.html'
    model = User
    form_class = forms.UserForm
    profile_form_class = forms.ProfileForm
    success_url = reverse_lazy('detail_profile')

    def get_context_data(self, **kwargs):
        context = super(UserUpdateView,
                        self).get_context_data(**kwargs)
        if self.request.POST:
            context['profile_form'] = self.profile_form_class(
                self.request.POST, instance=self.object.profile)
        else:
            context['profile_form'] = self.profile_form_class(
                instance=self.object.profile)
        return context

    def get_object(self):
        return self.request.user

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.form_class(request.POST, instance=self.object)
        profile_form = self.profile_form_class(
            request.POST, instance=self.object.profile)

        if form.is_valid() and profile_form.is_valid():
            user = form.save()
            profile_form.save(user)
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(
                self.get_context_data(form=form, profile_form=profile_form))


@method_decorator(login_required, name='dispatch')
class DownloadPDF(View):

    def render_to_pdf(self, template_src, context_dict={}):
        template = get_template(template_src)
        html = template.render(context_dict)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
        if not pdf.err:
            return HttpResponse(result.getvalue(), content_type='application/pdf')
        return None

    def get(self, request, *args, **kwargs):
        user = request.user
        profile = user.profile
        events = selectors.EventSelector().hosted(user)
        enrollments = models.Enrollment.objects.filter(created_by=user)
        ratings = models.Rating.objects.filter(created_by=user)
        transactions = models.Transaction.objects.filter(created_by=user)
        data = {
            "name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "date_join": user.date_joined,
            "location": profile.location,

            "picture": profile.picture,
            "birthdate": profile.birthdate,
            "token": profile.token,
            "eventpoints": profile.eventpoints,
            "bio": profile.bio,
            "events": events,
            "enrollments": enrollments,
            "ratings": ratings,
            "transactions": transactions,

        }
        pdf = self.render_to_pdf('profile/pdf.html', data)

        response = HttpResponse(pdf, content_type='application/pdf')
        filename = user.username+'-eventshow.pdf'
        content = "attachment; filename=%s" % (filename)
        response['Content-Disposition'] = content
        return response


def penalty(event, stripe_token):
    try:
        attendees = selectors.UserSelector().event_attendees(event.pk).count()
        fee = services.PaymentService().fee(round(event.price*100))
        services.PaymentService().charge(
            round(fee*attendees), stripe_token)

    except stripe.error.StripeError:
        redirect('payment_error')
