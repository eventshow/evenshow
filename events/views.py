from django.shortcuts import render
from datetime import datetime, date

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic

from . import forms
from . import models
from . import selectors
from . import services
from .forms_auth import UserCreationForm

EVENT_SUCCESS_URL = reverse_lazy('hosted_events')
User = get_user_model()


def index(request):
    return render(request, 'home.html', {'STATIC_URL': settings.STATIC_URL})


class AttendeeListView(generic.ListView):
    model = User
    template_name = 'user/list.html'

    def get(self, request, *args, **kwargs):
        host = request.user
        event_pk = kwargs.get('pk')


class AttendeePaymentView(generic.View):
    template_name = 'main/payment.html'

    def get(self, request, *args, **kwargs):
        if services.EventService.count(kwargs.get('pk')):
            pk = self.kwargs.get('pk')
            event = models.Event.objects.get(pk=pk)
            payment = event.price
            return render(request, self.template_name, {'payment': payment})
        else:
            return redirect('/')


class EventDetailView(generic.DetailView):
    model = models.Event
    template_name = 'event/detail.html'

    def get(self, request, *args, **kwargs):
        if services.EventService.count(kwargs.get('pk')):
            return super().get(self, request, *args, **kwargs)
        else:
            return redirect('/')

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super().get_context_data(**kwargs)
        event = kwargs.get('object')
        duration = event.duration

        if user.is_authenticated:
            user_is_enrolled = services.EnrollmentService.user_is_enrolled(
                event.pk, user)
            context['user_is_old_enough'] = event.min_age <= user.profile.age
        else:
            user_is_enrolled = False
            context['user_is_old_enough'] = True

        context['attendee_count'] = selectors.UserSelector.event_attendees(
            event.pk).count()
        context['duration'] = str(duration // 3600) + 'h ' + \
            str((duration // 60) % 60) + 'min'
        context['ratings'] = selectors.RatingSelector.on_event(
            event.pk)
        context['g_location'] = event.location.replace(' ', '+')

        context['user_is_enrolled'] = user_is_enrolled

        return context


@method_decorator(login_required, name='dispatch')
class EventCreateView(generic.CreateView):
    model = models.Event
    form_class = forms.EventCreateForm
    success_url = EVENT_SUCCESS_URL
    template_name = 'event/create.html'

    def get(self, request, *args, **kwargs):
        if services.EventService.can_create(self.request.user):
            return super().get(request, *args, **kwargs)
        else:
            return redirect('/')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = models.Category.objects.all()

        return context

    def form_valid(self, form):
        event = form.save(commit=False)
        services.EventService.create(event, self.request.user)
        return super(EventCreateView, self).form_valid(form)


@method_decorator(login_required, name='dispatch')
class EventDeleteView(generic.DeleteView):
    template_name = 'event/event_confirm_delete.html'
    model = models.Event
    success_url = EVENT_SUCCESS_URL

    def delete(self, request, *args, **kwargs):
        host = request.user
        event_pk = self.kwargs.get('pk')
        if services.EventService.count(event_pk) and services.EventService.user_is_owner(host, kwargs.get('pk')):
            self.object = self.get_object()
            self.object.delete()
            return redirect('hosted_events')
        else:
            return redirect('events')

    def get(self, request, *args, **kwargs):
        host = request.user
        event_pk = self.kwargs.get('pk')
        if services.EventService.count(event_pk) and services.EventService.user_is_owner(host, self.kwargs.get('pk')):
            return super().get(request, *args, **kwargs)
        else:
            return redirect('events')


@method_decorator(login_required, name='dispatch')
class EventHostedListView(generic.ListView):
    model = models.Event
    template_name = 'event/list.html'

    def get_queryset(self):
        return selectors.EventSelector.hosted(self.request.user)


@method_decorator(login_required, name='dispatch')
class EventEnrolledListView(generic.ListView):
    model = models.Event
    template_name = 'event/list.html'

    def get_queryset(self):
        return selectors.EventSelector.enrolled(self.request.user)


@method_decorator(login_required, name='dispatch')
class EventNotEnrolledListView(generic.ListView):
    model = models.Event
    template_name = 'event/list.html'

    def get_queryset(self):
        return selectors.EventSelector.not_enrolled(self.request.user)


@method_decorator(login_required, name='dispatch')
class EventUpdateView(generic.UpdateView):
    model = models.Event
    form_class = forms.EventUpdateForm
    success_url = EVENT_SUCCESS_URL
    template_name = 'event/update.html'

    def form_valid(self, form):
        host = self.request.user
        event_pk = self.kwargs.get('pk')
        if services.EventService.count(event_pk) and services.EventService.user_is_owner(host, event_pk):
            event = form.save(commit=False)
            services.EventService.update(event, host)
            return super(EventUpdateView, self).form_valid(form)
        else:
            return redirect('events')

    def get(self, request, *args, **kwargs):
        host = request.user
        event_pk = self.kwargs.get('pk')
        if services.EventService.count(event_pk) and services.EventService.user_is_owner(host, kwargs.get('pk')):
            return super().get(request, *args, **kwargs)
        else:
            return redirect('events')


def nearby_events(request, distance=None):
    distance = request.GET.get('distance', '')
    try:
        if distance:
            events = services.EventService.nearby_events_distance(distance)
        else:
            events = services.EventService.nearby_events_ordered()
    except ValueError:
        events = services.EventService.nearby_events_ordered()

    context = {'object_list': events, 'STATIC_URL': settings.STATIC_URL}

    return render(request, 'event/list_search.html', context)


def events_filter_ordered_by_distance(request, max_price, minimum_price, year, month, day):
    events_distances_ordered = services.EventService.events_filter_ordered_by_distance(
        max_price, minimum_price, year, month, day)
    context = {'object_list': events_distances_ordered}

    return render(request, 'event/list.html', context)


@method_decorator(login_required, name='dispatch')
class EnrollmentCreateView(generic.View):
    model = models.Enrollment

    def get(self, request, *args, **kwargs):
        attendee = self.request.user
        event_pk = kwargs.get('pk')

        if services.EventService.count(event_pk) and not services.EnrollmentService.user_is_enrolled(event_pk,
                                                                                                     attendee):
            services.EnrollmentService.create(event_pk, attendee)

            return render(request, 'event/thanks.html')
        else:
            return redirect('/')


@method_decorator(login_required, name='dispatch')
class EnrollmentListView(generic.ListView):
    model = models.Enrollment
    template_name = 'enrollment/list.html'

    def get(self, request, *args, **kwargs):
        host = request.user
        event_pk = kwargs.get('pk')

        if services.EventService.count(event_pk) and services.EventService.user_is_owner(host, event_pk):
            return super().get(request, *args, **kwargs)
        else:
            return redirect('events')

    def get_queryset(self):
        return selectors.EnrollmentSelector.on_event(self.kwargs.get('pk'), 'PENDING')


@method_decorator(login_required, name='dispatch')
class EnrollmentUpdateView(generic.View):
    model = models.Enrollment
    template_name = 'enrollment/list.html'

    def get(self, request, *args, **kwargs):
        host = self.request.user

        if services.EnrollmentService.count(kwargs.get('pk')) and self.updatable(host):
            services.EnrollmentService.update(
                kwargs.get('pk'), host, kwargs.get('status'))
            event_pk = selectors.EventSelector.with_enrollment(
                kwargs.get('pk')).values_list('pk', flat=True).first()

            return redirect('event_attendees', event_pk)
        else:
            return redirect('/')

    def updatable(self, host):
        enrollment_pk = self.kwargs.get('pk')
        return services.EnrollmentService.host_can_update(host,
                                                          enrollment_pk) and services.EnrollmentService.is_pending(
            enrollment_pk)


@method_decorator(login_required, name='dispatch')
class RatingCreateHost(generic.CreateView):
    template_name = 'rating/rating_host.html'
    model = models.Rating
    form_class = forms.RatingForm
    success_url = '/home'

    def get(self, request, *args, **kwargs):
        created_by = request.user
        event = models.Event.objects.get(pk=self.kwargs.get('event_pk'))
        exist_already_rating = selectors.RatingSelector.exists_this_rating_for_this_user_and_event(created_by, event,
                                                                                                   event.created_by)
        is_enrolled_for_this_event = selectors.EnrollmentSelector.enrolled_for_this_event(
            created_by, event)
        if (not exist_already_rating) and is_enrolled_for_this_event:
            return super().get(self, request, args, *kwargs)
        else:
            return redirect('events')

    def get_context_data(self, **kwargs):
        context = super(RatingCreateHost, self).get_context_data(**kwargs)
        context['event_pk'] = self.kwargs.get('event_pk')
        return context

    def form_valid(self, form):
        rating = form.save(commit=False)
        event = models.Event.objects.get(id=self.kwargs.get('event_pk'))
        host = selectors.UserSelector.event_host(self.kwargs.get('event_pk'))
        created_by = self.request.user

        rating.created_by = created_by
        rating.reviewed = host
        rating.event = event
        rating.on = 'HOST'

        if services.RatingService.is_valid_rating(rating, event, created_by):
            services.RatingService.create(rating)
            return super().form_valid(form)
        else:
            return redirect('home')


@method_decorator(login_required, name='dispatch')
class RatingCreateAttendant(generic.CreateView):
    template_name = 'rating/rating_attendee.html'
    model = models.Rating
    form_class = forms.RatingForm
    success_url = '/home'

    def get(self, request, *args, **kwargs):
        created_by = request.user
        event = models.Event.objects.get(pk=self.kwargs.get('event_pk'))
        attendee_id = self.kwargs.get('event_pk')
        exist_already_rating = selectors.RatingSelector.exists_this_rating_for_this_user_and_event(created_by,
                                                                                                   event,
                                                                                                   attendee_id)
        is_owner_of_this_event = selectors.EventSelector.is_owner(
            created_by, event.id)
        if (not exist_already_rating) and is_owner_of_this_event:
            return super().get(self, request, args, *kwargs)
        else:
            return redirect('home')

    def get_context_data(self, **kwargs):
        context = super(RatingCreateAttendant, self).get_context_data(**kwargs)
        context['event_pk'] = self.kwargs.get('event_pk')
        context['attendee_pk'] = self.kwargs.get('attendee_pk')

        return context

    def form_valid(self, form):
        rating = form.save(commit=False)
        event = models.Event.objects.get(id=self.kwargs.get('event_pk'))
        host = selectors.UserSelector.event_host(self.kwargs.get('event_pk'))
        created_by = self.request.user

        rating.created_by = created_by

        reviewed = models.User.objects.get(id=self.kwargs.get('attendee_pk'))
        rating.reviewed = reviewed
        rating.event = event
        rating.on = 'ATTENDEE'

        if services.RatingService.is_valid_rating(rating, event, created_by):
            services.RatingService.create(rating)
            return super().form_valid(form)
        else:
            return redirect('events')


class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        user = form.save()
        services.ProfileService.create(user, None)
        login(self.request, user, backend=settings.AUTHENTICATION_BACKENDS[1])
        return redirect('/'), {'STATIC_URL': settings.STATIC_URL}


def attendees_list(request, event_pk):
    event = models.Event.objects.get(id=event_pk)

    if event.created_by == request.user:
        attendees = selectors.UserSelector.event_attendees(event_pk)

        context = {'attendees': attendees, 'event': event_pk}

        return render(request, 'rating/attendees_list.html', context)
    else:
        return redirect('/home')


# Create your views here.
