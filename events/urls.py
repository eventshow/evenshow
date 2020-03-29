from django.urls import path, re_path
from django.views.generic.base import TemplateView

from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('home', views.HomeView.as_view(), name='home'),

    path('auth/signup/', views.SignUpView.as_view(), name='signup'),

    path('enrollments/<int:pk>/update',
         views.EnrollmentUpdateView.as_view(), name='update_enrollment'),

    path('events/enrolled',
         views.EventEnrolledListView.as_view(), name='enrolled_events'),
    path('events/hosted', views.EventHostedListView.as_view(),
         name='hosted_events'),
    re_path(r'^events/(?P<date>\d{1,2}/\d{1,2}/\d{4})?/(?P<location>.*)?/(?P<start_hour>\d{1,2}:\d{1,2})?$',
            views.EventSearchByLocationDateStartHourView.as_view(), name='event_search_home'),
    path('events/nearby',
         views.EventSearchNearbyView.as_view(), name='event_nearby_search_home'),
    path('events/create', views.EventCreateView.as_view(),
         name='create_event'),
    path('events/payment/<int:pk>',
         views.AttendeePaymentView.as_view(), name='attendee_payment'),
    path('events/<int:pk>', views.EventDetailView.as_view(), name='detail_event'),
    path('events/<int:pk>/attendees',
         views.AttendeeListView.as_view(), name='list_attendees'),
    path('events/<int:pk>/enrollments',
         views.EnrollmentListView.as_view(), name='list_enrollments'),
    path('events/<int:pk>/enroll',
         views.EnrollmentCreateView.as_view(), name='enroll_event'),
    path('events/<int:pk>/delete', views.EventDeleteView.as_view(),
         name='delete_event'),
    path('events/<int:pk>/update', views.EventUpdateView.as_view(),
         name='update_event'),

    path('profile', views.UserDetailView.as_view(),
         name='detail_profile'),
    path('profile/update', views.UserUpdateView.as_view(),
         name='update_profile'),

    path('ratings/new/host/<int:event_pk>',
         views.RateHostView.as_view(), name='create_rating_host'),
    re_path(r'^ratings/new/attendee/(?P<event_pk>\d+)?/(?P<attendee_pk>\d+)?/?$',
            views.RateAttendeeView.as_view(), name='create_rating_attendee'),

    path('my_transaction', views.TransactionListView.as_view(),
         name='my_transaction'),

    path('vista/gracias', TemplateView.as_view(template_name='event/thanks.html'),
         name='gracias'),

    path('preferences', views.preferences, name='preferences'),

     path('profile/', TemplateView.as_view(template_name='registration/personal_data.html'), name='personal_data'),

    path('edit/profile/', TemplateView.as_view(template_name='registration/edit_profile.html'), name='edit_profile'),

    path('edit/password/', TemplateView.as_view(template_name='registration/edit_password.html'), name='edit_password'),
    path('bills', TemplateView.as_view(template_name='user/bills.html'),
         name='bills'),
    path('referred', TemplateView.as_view(template_name='user/referred.html'),
         name='referred'),

    path('profile/eventpoints', views.PointsView.as_view(), name='points'),
]
