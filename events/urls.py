from django.urls import path, re_path
from django.views.generic.base import TemplateView

from . import views

urlpatterns = [
    path('auth/signup/', views.SignUpView.as_view(), name='signup'),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('home', TemplateView.as_view(template_name='home.html'), name='home'),

    path('enrollments/<int:pk>/update/<str:status>',
         views.EnrollmentUpdateView.as_view(), name='update_enrollment'),
    path('events', views.EventNotEnrolledListView.as_view(), name='events'),
    path('events/enrolled',
         views.EventEnrolledListView.as_view(), name='enrolled_events'),
    path('events/hosted', views.EventHostedListView.as_view(),
         name='hosted_events'),
    re_path(r'^events/nearby/(?P<distance>\d+)?/?$',
            views.nearby_events, name='nearby_events'),
    path('events/create', views.EventCreateView.as_view(),
         name='create_event'),
    path('events/payment/<int:pk>',
         views.AttendeePaymentView.as_view(), name='attendee_payment'),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='detail_event'),
    path('events/<str:max_price>/<str:minimum_price>/<int:year>/<int:month>/<int:day>',
         views.events_filter_ordered_by_distance, name='filtered_events'),
    path('events/<int:pk>/attendees',
         views.EnrollmentListView.as_view(), name='event_attendees'),
    path('events/<int:pk>/enroll',
         views.EnrollmentCreateView.as_view(), name='enroll_event'),
    path('events/<int:pk>/delete', views.EventDeleteView.as_view(),
         name='delete_event'),
    path('events/<int:pk>/update', views.EventUpdateView.as_view(),
         name='update_event'),

    path('ratings/new/host/<int:event_pk>',
         views.RateHostView.as_view(), name='create_rating_host'),
    re_path(r'^ratings/new/attendee/(?P<event_pk>\d+)?/(?P<attendee_pk>\d+)?/?$',
            views.RateAttendeeView.as_view(), name='create_rating_attendee'),
    re_path(r'^ratings/host/list/(?P<event_pk>\d+)?/?$',
            views.attendees_list, name='list_attendees'),
]
