from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views
from django.conf.urls import handler404
from django.conf.urls.static import static
from django.urls import include, path, reverse_lazy

from events.forms import LoginForm, PasswordUpdateForm

urlpatterns = [
    path('', include('events.urls')),
    path('admin/', admin.site.urls),
    path('auth/', include('django.contrib.auth.urls')),
    path('auth/login', views.LoginView.as_view(authentication_form=LoginForm), name='login'),
    path('auth/update/password',
         views.PasswordChangeView.as_view(template_name='profile/update_password.html', form_class=PasswordUpdateForm, success_url=reverse_lazy('detail_profile')), name='update_password')
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'events.views.handler_404'
