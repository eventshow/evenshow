from django.contrib.auth.decorators import login_required
from django.urls import path, re_path
from django.views.generic.base import TemplateView

from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('home', views.HomeView.as_view(), name='home'),

    path('auth/signup/', views.SignUpView.as_view(), name='signup'),

    path('enrollments/thanks', TemplateView.as_view(template_name='enrollment/thanks.html'),
         name='thanks'),
    path('enrollments/<int:pk>/delete',
         views.EnrollmentDeleteView.as_view(), name='delete_enrollment'),
    path('enrollments/<int:pk>/update',
         views.EnrollmentUpdateView.as_view(), name='update_enrollment'),

    path('events/enrolled',
         views.EventEnrolledListView.as_view(), name='enrolled_events'),
    path('events/hosted', views.EventHostedListView.as_view(),
         name='hosted_events'),
    path('events/filter', views.EventFilterFormView.as_view(), name='event_filter'),
    re_path(r'^events/(?:(?P<date>\d{4}-\d{2}-\d{2})/)?(?:(?P<location>[a-zA-Z\u00C0-\u00FF\s]*)/)?(?:(?P<start_hour>\d{2}:\d{2}:\d{2})/)?(?:min(?P<min_price>\d*.?(.\d{1,2})?)/)?(?:max(?P<max_price>\d*.?(.\d{1,2})?)/)?$',
            views.EventFilterListView.as_view(), name='list_event_filter'),

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

    path('profile', login_required(TemplateView.as_view(template_name='profile/detail.html')),
         name='detail_profile'),
    path('profile/delete', views.UserDeleteView.as_view(), name='delete_profile'),
    path('profile/referred',
         login_required(TemplateView.as_view(template_name='profile/referred.html')), name='referred'),
    path('profile/receipts', views.TransactionListView.as_view(),
         name='receipts'),
    path('profile/update', views.UserUpdateView.as_view(),
         name='update_profile'),

    path('ratings/new/host/<int:event_pk>',
         views.RateHostView.as_view(), name='create_rating_host'),
    re_path(r'^ratings/new/attendee/(?P<event_pk>\d+)?/(?P<attendee_pk>\d+)?/?$',
            views.RateAttendeeView.as_view(), name='create_rating_attendee'),

    path('ups', TemplateView.as_view(template_name='not_impl.html'),
         name='not_impl'),

    path('profile/pdf_download', views.DownloadPDF.as_view(), name='pdf_download'),

     path('vista/gracias', TemplateView.as_view(template_name='enrollment/thanks.html'),
         name='grac'),

]
