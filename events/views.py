import stripe

from datetime import datetime, date, time

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.generic import TemplateView
from django.views.generic.list import MultipleObjectMixin

from . import forms
from . import models
from . import selectors
from . import services

stripe.api_key = settings.STRIPE_SECRET_KEY

EVENT_SUCCESS_URL = reverse_lazy('hosted_events')
User = get_user_model()


def index(request):
    return render(request, 'home.html', {'STATIC_URL': settings.STATIC_URL})

class HomeView(generic.FormView):
    form_class = forms.SearchHomeForm
    template_name = 'home.html'

    def get_success_url(self):
        request = self.request.POST
        date = request.get('date')
        location = request.get('location')
        start_hour = request.get('start_hour')
        return reverse_lazy('event_search_home', kwargs={
            'date': date,
            'location': location,
            'start_hour': start_hour
        }
        )


@method_decorator(login_required, name='dispatch')
class AttendeeListView(generic.ListView):
    model = User
    template_name = 'attendee/list.html'
    paginate_by = 5

    def get(self, request, *args, **kwargs):
        if services.EventService().user_is_owner(request.user, kwargs.get('event_pk')):
            return super(AttendeeListView, self).get(self, request, *args, **kwargs)
        else:
            return redirect('/')

    def get_context_data(self, **kwargs):
        event_pk = self.kwargs.get('event_pk')
        event = models.Event.objects.get(pk=event_pk)
        context = super(AttendeeListView, self).get_context_data(**kwargs)
        context['event_has_finished'] = event.has_finished
        context['event_has_started'] = event.has_started
        context['event_pk'] = event_pk
        context['rated_attendees'] = selectors.UserSelector(
        ).rated_on_event(event_pk)
        return context

    def get_queryset(self):
        queryset = super(AttendeeListView, self).get_queryset()
        queryset = selectors.UserSelector().event_attendees(self.kwargs.get('event_pk'))
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
    paginate_by = 5

    def get(self, request, *args, **kwargs):
        if services.EventService().count(kwargs.get('pk')):
            return super().get(self, request, *args, **kwargs)
        else:
            return redirect('/')

    def get_context_data(self, **kwargs):
        user = self.request.user
        event = kwargs.get('object')
        object_list = selectors.RatingSelector().on_event(
            event.pk)
        context = super(EventDetailView, self).get_context_data(
            object_list=object_list, **kwargs)
        duration = event.duration

        event_is_full = selectors.UserSelector().event_attendees(
            event.pk).count() >= event.capacity
        user_can_enroll = True

        if user.is_authenticated:
            user_can_enroll = services.EnrollmentService().user_can_enroll(
                event.pk, user)

        hours, minutes = divmod(duration, 60)
        context['duration'] = '{0}h {1}min'.format(hours, minutes)
        context['gmaps_key'] = settings.GOOGLE_API_KEY
        context['stripe_key'] = settings.STRIPE_PUBLISHABLE_KEY
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
            self.object.delete()
            return redirect('hosted_events')
        else:
            return redirect('/')

    def get(self, request, *args, **kwargs):
        host = request.user
        event_pk = self.kwargs.get('pk')
        if services.EventService().count(event_pk) and services.EventService().user_is_owner(host,
                                                                                             self.kwargs.get('pk')):
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
    model = models.Event
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
        queryset = selectors.EventSelector().enrolled(self.request.user)
        return queryset


@method_decorator(login_required, name='dispatch')
class EventNotEnrolledListView(generic.ListView):
    model = models.Event
    template_name = 'event/list.html'

    def get_queryset(self):
        return selectors.EventSelector().not_enrolled(self.request.user)


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
            services.EventService().update(event, host)
            return super(EventUpdateView, self).form_valid(form)
        else:
            return redirect('events')

    def get(self, request, *args, **kwargs):
        host = request.user
        event_pk = self.kwargs.get('pk')
        if services.EventService().count(event_pk) and services.EventService().user_is_owner(host, kwargs.get('pk')):
            return super().get(request, *args, **kwargs)
        else:
            return redirect('/')


class EventSearchByLocationDateStartHourView(generic.ListView):
    model = models.Event
    template_name = 'event/list_search.html'
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super(EventSearchByLocationDateStartHourView,
                        self).get_context_data(**kwargs)
        context['length'] = len(self.get_queryset())
        return context

    def get_queryset(self):
        queryset = super(
            EventSearchByLocationDateStartHourView, self).get_queryset()
        es_date = self.kwargs.get('date')
        if es_date and es_date != '':
            date = datetime.strptime(
                es_date, '%d/%m/%Y').strftime('%Y-%m-%d')
        else:
            date = es_date
        location = self.kwargs.get('location')
        start_hour = self.kwargs.get('start_hour')
        queryset = services.EventService().events_filter_home(
            self, location, date, start_hour)
        return queryset


class EventSearchNearbyView(generic.ListView):
    model = models.Event
    template_name = 'event/list_search.html'
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super(EventSearchNearbyView, self).get_context_data(**kwargs)
        context['length'] = len(self.get_queryset())
        return context

    def get_queryset(self):
        queryset = super(EventSearchNearbyView, self).get_queryset()
        queryset = services.EventService().nearby_events_distance(self, 50000)
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

        event_exists = services.EventService().count(event_pk)
        event_is_full = selectors.UserSelector().event_attendees(
            event_pk).count() >= models.Event.objects.get(pk=event_pk).capacity
        user_can_enroll = services.EnrollmentService().user_can_enroll(
            event_pk, attendee)

        context = {'event_title': models.Event.objects.get(pk=event_pk)}

        if event_exists and user_can_enroll and not event_is_full:
            services.EnrollmentService().create(event_pk, attendee)

            stripe.Charge.create(
                amount=500,
                currency='eur',
                description='Comprar entrada para evento',
                source=request.POST['stripeToken']
            )

            return render(request, 'event/thanks.html', context)
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
            return super().get(request, *args, **kwargs)
        else:
            return redirect('events')

    def get_queryset(self):
        return selectors.EnrollmentSelector().on_event(self.kwargs.get('pk'), 'PENDING')


@method_decorator(login_required, name='dispatch')
class EnrollmentUpdateView(generic.View):
    model = models.Enrollment
    template_name = 'enrollment/list.html'

    def get(self, request, *args, **kwargs):
        host = self.request.user

        if services.EnrollmentService().count(kwargs.get('pk')) and self.updatable(host):
            services.EnrollmentService().update(
                kwargs.get('pk'), host, kwargs.get('status'))
            event_pk = selectors.EventSelector().with_enrollment(
                kwargs.get('pk')).values_list('pk', flat=True).first()

            return redirect('event_attendees', event_pk)
        else:
            return redirect('/')

    def updatable(self, host):
        enrollment_pk = self.kwargs.get('pk')
        return services.EnrollmentService().host_can_update(host,
                                                            enrollment_pk) and services.EnrollmentService().is_pending(
            enrollment_pk)


@method_decorator(login_required, name='dispatch')
class RateHostView(generic.CreateView):
    template_name = 'rating/rating_host.html'
    model = models.Rating
    form_class = forms.RatingForm
    success_url = '/events/enrolled'

    def get(self, request, *args, **kwargs):
        created_by = request.user
        event = models.Event.objects.get(pk=self.kwargs.get('event_pk'))
        exist_already_rating = selectors.RatingSelector().exists_this_rating_for_this_user_and_event(created_by, event,
                                                                                                     event.created_by)

        is_enrolled_for_this_event = event in selectors.EventSelector().enrolled(self.request.user)

        if (not exist_already_rating) and is_enrolled_for_this_event and event.has_finished:
            return super().get(self, request, args, *kwargs)
        else:
            return redirect('home')

    def get_context_data(self, **kwargs):
        context = super(RateHostView, self).get_context_data(**kwargs)
        context['event_pk'] = self.kwargs.get('event_pk')
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
    template_name = 'rating/rating_attendee.html'
    model = models.Rating
    form_class = forms.RatingForm

    def get(self, request, *args, **kwargs):
        created_by = request.user
        event = models.Event.objects.get(pk=self.kwargs.get('event_pk'))
        attendee_id = self.kwargs.get('attendee_pk')
        attendee = models.User.objects.get(id=attendee_id)
        exist_already_rating = selectors.RatingSelector().exists_this_rating_for_this_user_and_event(created_by,
                                                                                                     event,
                                                                                                     attendee_id)
        is_owner_of_this_event = selectors.EventSelector().is_owner(
            created_by, event.id)
        attendee_enrolled_for_this_event = event in selectors.EventSelector().enrolled(attendee)
        if (not exist_already_rating) and is_owner_of_this_event and attendee_enrolled_for_this_event and event.has_finished:
            return super().get(self, request, args, *kwargs)
        else:
            return redirect('home')

    def get_context_data(self, **kwargs):
        context = super(RateAttendeeView, self).get_context_data(**kwargs)
        context['event_pk'] = self.kwargs.get('event_pk')
        context['attendee_pk'] = self.kwargs.get('attendee_pk')
        context['attendee_name'] = models.User.objects.get(
            id=self.kwargs.get('attendee_pk')).username
        context['event_title'] = models.Event.objects.get(
            id=self.kwargs.get('event_pk')).title

        return context

    def get_success_url(self):
        return reverse_lazy('list_attendees', kwargs={'event_pk': self.kwargs.get('event_pk')})

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
        services.ProfileService().create(user, birthdate)
        login(self.request, user, backend=settings.AUTHENTICATION_BACKENDS[1])
        return super(SignUpView, self).form_valid(form)
