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

from . import forms
from . import models
from . import selectors
from . import services

stripe.api_key = settings.STRIPE_SECRET_KEY

EVENT_SUCCESS_URL = reverse_lazy('hosted_events')
User = get_user_model()


def index(request):
    return render(request, 'home.html', {'STATIC_URL': settings.STATIC_URL})


class HomeView(TemplateView):
    form = forms.SearchHomeForm()
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = self.form
        context['STATIC_URL'] = settings.STATIC_URL
        return render(request, self.template_name, context)


class AttendeeListView(generic.ListView):
    model = User
    template_name = 'user/list.html'

    def get(self, request, *args, **kwargs):
        host = request.user
        event_pk = kwargs.get('pk')


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


class EventDetailView(generic.DetailView):
    model = models.Event
    template_name = 'event/detail.html'

    def get(self, request, *args, **kwargs):
        if services.EventService().count(kwargs.get('pk')):
            return super().get(self, request, *args, **kwargs)
        else:
            return redirect('/')

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super().get_context_data(**kwargs)
        event = kwargs.get('object')
        duration = event.duration

        event_is_full = selectors.UserSelector().event_attendees(
            event.pk).count() >= event.capacity
        user_can_enroll = True

        if user.is_authenticated:
            user_can_enroll = services.EnrollmentService().user_can_enroll(
                event.pk, user)

        hours, minutes = divmod(duration, 60)
        context['duration'] = '{0}h {1}min'.format(hours, minutes)
        context['ratings'] = selectors.RatingSelector().on_event(
            event.pk)
        context['g_location'] = event.location.replace(' ', '+')
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

    def get(self,request,*args,**kwargs):
        events = selectors.EventSelector().hosted(self.request.user)
        page = request.GET.get('page',1)

        paginator  = Paginator(events, 5)

        try:
            events = paginator.page(page)
        except PageNotAnInteger:
            events= paginator.page(1)
        except EmptyPage:
            events = paginator.page(paginator.num_pages)
            
        context = {'object_list': events}
            
        return render(request, self.template_name, context)
         
        
    


@method_decorator(login_required, name='dispatch')
class EventEnrolledListView(generic.ListView):
    model = models.Event
    template_name = 'event/list.html'

    def get(self,request,*args,**kwargs):
        events = selectors.EventSelector().enrolled(self.request.user)
        page = request.GET.get('page',1)

        paginator  = Paginator(events, 5)

        try:
            events = paginator.page(page)
        except PageNotAnInteger:
            events= paginator.page(1)
        except EmptyPage:
            events = paginator.page(paginator.num_pages)
            
        context = {'object_list': events}
            
        return render(request, self.template_name, context)


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
    template_name = 'event/list_search.html'
    form = forms.SearchHomeForm()

    def get(self, request, *args, **kwargs):
        location = request.GET.get('location', None)
        event_date = request.GET.get('date', None)
        start_hour = request.GET.get('start_hour', None)

        home_template = 'home.html'

        errors = []
        events = []
        length = 0
        fecha = ""

        if event_date != '':
            try:
                fecha = datetime.strptime(event_date, '%d/%m/%Y').date()
                if fecha < date.today():
                    errors.append("Introduzca una fecha futura")
                    template_name = home_template
            except ValueError:
                errors.append("Introduzca una fecha con el patrón válido")
                template_name = home_template

        if start_hour != '':
            try:
                datetime.strptime(start_hour, '%H:%M').time()
            except ValueError:
                errors.append("Introduzca una hora válida")
                template_name = home_template

        if not errors:
            events = services.EventService().events_filter_home(
                self, location, fecha, start_hour)
            template_name = self.template_name

            length = len(events)

            page = request.GET.get('page', 1)
            paginator = Paginator(events, 12)

            try:
                events = paginator.page(page)
            except PageNotAnInteger:
                events = paginator.page(1)
            except EmptyPage:
                events = paginator.page(paginator.num_pages)

        return render(request, template_name,
                      {'object_list': events, 'STATIC_URL': settings.STATIC_URL, 'errors': errors, 'place': location,
                       'length': length, 'form': self.form})


class EventSearchNearbyView(generic.ListView):
    template_name = 'event/list_search.html'

    def get(self, request, *args, **kwargs):
        events = services.EventService.nearby_events_distance(self, 50000)
        length = len(events)

        page = request.GET.get('page', 1)
        paginator = Paginator(events, 12)

        try:
            events = paginator.page(page)
        except PageNotAnInteger:
            events = paginator.page(1)
        except EmptyPage:
            events = paginator.page(paginator.num_pages)

        return render(request, self.template_name,
                      {'object_list': events, 'STATIC_URL': settings.STATIC_URL, 'length': length})


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
            print('-------------------')
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

        is_enrolled_for_this_event = selectors.EnrollmentSelector().enrolled_for_this_event(
            created_by, event)

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
    success_url = '/events/hosted'

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
        is_enrolled_for_this_event = selectors.EnrollmentSelector().enrolled_for_this_event(
            attendee, event)
        if (not exist_already_rating) and is_owner_of_this_event and is_enrolled_for_this_event and event.has_finished:
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


def attendees_list(request, event_pk):
    event = models.Event.objects.get(id=event_pk)
    page = request.GET.get('page', 1)

    if event.created_by == request.user:
        attendees = selectors.UserSelector().event_attendees(event_pk)

        paginator = Paginator(attendees, 5)

        try:
            attendees = paginator.page(page)
        except PageNotAnInteger:
            attendees = paginator.page(1)
        except EmptyPage:
            attendees = paginator.page(paginator.num_pages)

        context = {'attendees': attendees,
                   'event': event_pk, 'event_title': event.title}

        return render(request, 'rating/attendees_list.html', context)
    else:
        return redirect('/home')
