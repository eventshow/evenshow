from django.db.models import Count
from datetime import date, datetime, timezone

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.generic.edit import FormMixin, ModelFormMixin
from django.views.generic.list import MultipleObjectMixin
from django.views.defaults import page_not_found

from . import forms
from . import models
from . import selectors
from . import services
from .models import Event

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

    def get_success_url(self):
        request = self.request.POST
        date = request.get('date')
        location = request.get('location')
        start_hour = request.get('start_hour')

        if self.request.session.get('form_values'):
            del self.request.session['form_values']

        return reverse_lazy('list_event_filter', kwargs={
            'date': date,
            'location': location,
            'start_hour': start_hour,
        }
        )


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
        queryset = super(AttendeeListView, self).get_queryset()
        queryset = selectors.UserSelector().event_attendees(self.kwargs.get('pk'))
        return queryset


class AttendeePaymentView(generic.View):
    template_name = 'main/payment.html'

    def get(self, request, *args, **kwargs):
        if services.EventService().count(kwargs.get('pk')):
            pk = self.kwargs.get('pk')
            event = models.Event.objects.get(pk=pk)
            payment = event.price
            return render(request, self.template_name, {'payment': payment})
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

            user_can_enroll = not context.get('user_is_enrolled') and context.get(
                'user_is_old_enough') and not context.get('user_is_owner')

        hours, minutes = divmod(duration, 60)
        context['duration'] = '{0}h {1}min'.format(hours, minutes)
        context['gmaps_key'] = settings.GOOGLE_API_KEY
        context['stripe_key'] = settings.STRIPE_PUBLISHABLE_KEY
        context['event_is_full'] = event_is_full

        context['user_can_enroll'] = not event_is_full and user_can_enroll

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

    def delete(self, request, *args, **kwargs):
        host = request.user
        event_pk = self.kwargs.get('pk')
        if services.EventService().count(event_pk) and services.EventService().user_is_owner(host, kwargs.get('pk')):
            self.object = self.get_object()
            event = models.Event.objects.get(pk=event_pk)
            subject = 'Evento cancelado'
            body = 'El evento ' + event.title + 'en el que estás inscrito ha sido cancelado'
            recipient_list_queryset = selectors.UserSelector().event_attendees(event_pk)
            recipient_list = list(
                recipient_list_queryset.values_list('email', flat=True))
            # services.EmailService().send_email(subject, body, recipient_list)
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
        queryset = super(EventHostedListView, self).get_queryset()
        queryset = selectors.EventSelector().hosted(self.request.user)
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
        queryset = super(EventEnrolledListView, self).get_queryset()
        queryset = selectors.EnrollmentSelector().created_by(self.request.user)
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
            subject = 'Evento actualizado'
            body = 'El evento ' + event_db.title + \
                   'en el que estás inscrito ha sido actualizado'
            recipient_list_queryset = selectors.UserSelector().event_attendees(event_pk)
            recipient_list = list(
                recipient_list_queryset.values_list('email', flat=True))
            # services.EmailService().send_email(subject, body, recipient_list)
            services.EventService().update(event, host)
            return super(EventUpdateView, self).form_valid(form)
        else:
            return redirect('events')

    def get(self, request, *args, **kwargs):
        host = request.user
        event_pk = self.kwargs.get('pk')

        if services.EventService().count(event_pk) and services.EventService().user_is_owner(host, kwargs.get(
                'pk')) and not services.EventService().has_finished(event_pk):
            return super().get(request, *args, **kwargs)
        else:
            return redirect('/')


class EventFilterFormView(generic.FormView):
    form_class = forms.SearchFilterForm
    template_name = 'event/list_search.html'

    def get_success_url(self):
        request = self.request.POST
        date = request.get('date')
        location = request.get('location')
        start_hour = request.get('start_hour')
        min_price = request.get('min_price')
        max_price = request.get('max_price')
        self.request.session['form_values'] = request

        return reverse_lazy('list_event_filter', kwargs={
            'date': date,
            'location': location,
            'start_hour': start_hour,
            'min_price': min_price,
            'max_price': max_price
        }
        )


class EventFilterListView(generic.ListView):
    model = models.Event
    template_name = 'event/list_search.html'
    paginate_by = 12
    form_class = forms.SearchFilterForm

    def get_context_data(self, **kwargs):
        context = super(EventFilterListView,
                        self).get_context_data(**kwargs)
        context['locations'] = services.EventService().locations()
        context['location'] = self.kwargs['location_city__icontains']

        context['form'] = self.form_class(
            self.request.session.get('form_values'))
        context['categories'] = set(list(context.get(
            'object_list').annotate(total=Count('category')).values_list('category__name', 'total')))

        return context

    def get_queryset(self):
        queryset = super(
            EventFilterListView, self).get_queryset()
        self.kwargs['start_day'] = self.kwargs.pop('date', None)
        date = self.kwargs['start_day']
        if date:
            self.kwargs['start_day'] = datetime.strptime(
                date, '%d/%m/%Y').strftime('%Y-%m-%d')

        self.kwargs['location_city__icontains'] = self.kwargs.pop(
            'location', None)
        self.kwargs['start_time__gte'] = self.kwargs.pop('start_hour', None)
        self.kwargs['price__gte'] = self.kwargs.pop('min_price', None)
        self.kwargs['price__lte'] = self.kwargs.pop('max_price', None)

        queryset = services.EventService().events_filter_search(
            self.request.user, **self.kwargs)

        return queryset


class EventSearchNearbyView(generic.ListView):
    model = models.Event
    template_name = 'event/list_search.html'
    paginate_by = 12
    form_class = forms.SearchFilterForm

    def post(self, request, *args, **kwargs):
        latitude = self.request.POST.get('latitude')
        longitude = self.request.POST.get('longitude')
        queryset = self.get_queryset()
        context = {}
        context['latitude'] = latitude
        context['longitude'] = longitude
        context['form'] = self.form_class
        context['object_list'] = queryset

        if not queryset:
            context['location'] = "Su navegador no tiene activada la geolocalización. Por favor actívela para ver los eventos cercanos."

        return render(request, self.template_name, context)

    def get_queryset(self):
        queryset = super(EventSearchNearbyView, self).get_queryset()
        latitude = self.request.POST.get('latitude')
        longitude = self.request.POST.get('longitude')
        if latitude and longitude:
            queryset = services.EventService().nearby_events_distance(
                self, 50000, latitude, longitude)
        else:
            queryset = []
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

            stripe.Charge.create(
                amount=int(event.price*100),
                currency='eur',
                description='Comprar entrada para evento',
                source=request.POST['stripeToken']
            )

            event = models.Event.objects.get(pk=event_pk)
            services.UserService().add_bonus(attendee, event.price)

            subject = 'Nueva inscripción a {0}'.format(event.title)
            body = 'El usuario {0} se ha inscrito a tu evento {1} en Eventshow'.format(
                enrollment.created_by.username, event.title)
            recipient = event.created_by.email

            # services.EmailService().send_email(subject, body, [recipient])

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
            if (enrollment.created_at.replace(tzinfo=None) - (datetime.now())).days > 3:
                selectors.TransactionSelector().user_on_event(user, event).delete()
            enrollment.delete()

            subject = 'Asistencia a {0} cancelada'.format(event.title)
            body = 'El usuario {0} ha cancelado su asistencia a tu evento {1} en Eventshow'.format(
                user.username, event.title)
            recipient = event.created_by.email

            # services.EmailService().send_email(subject, body, [recipient])

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

        if services.EnrollmentService().count(enrollment_pk) and self.updatable(host) and (status == 'ACCEPTED' or status == 'REJECTED'):
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

            # services.EmailService().send_email(
            # subject, body, [recipient.email])

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
            auto_rating = self.request.user.id == event.created_by.id
            if (not exist_already_rating) and is_enrolled_for_this_event and event.has_finished and (not auto_rating):
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
        if services.RatingService().is_valid_rating(rating, event, created_by):
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
                    not auto_rating):
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

        if services.RatingService().is_valid_rating(rating, event, created_by):
            services.RatingService().create(rating)
            return super().form_valid(form)
        else:
            return redirect('home')


class SignUpView(generic.CreateView):
    form_class = forms.RegistrationForm
    success_url = reverse_lazy('home')
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
class TransactionListView(generic.ListView):
    model = models.Transaction
    template_name = 'profile/receipts.html'
    paginate_by = 5

    def get_queryset(self):
        super(TransactionListView, self).get_queryset()
        queryset = selectors.TransactionSelector().my_transaction(self.request.user)
        return queryset


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
