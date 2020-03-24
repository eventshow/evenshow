from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import Category, Event, Rating

CHOICES_YES_NO = ((0, "No"), (1, "Sí"))

CHOICES_SCORE = (('--'," " ),(1, 1), (2, 2), (3, 3), (4, 4), (5, 5))

User = get_user_model()


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        exclude = ['event', 'on', 'created_by', 'reviewed']
        widgets = {
            'score': forms.Select(choices=CHOICES_SCORE),
            'comment': forms.Textarea(attrs={'placeholder': '-'}),
        }


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        exclude = ['created_by', 'attendees']


class EventCreateForm(forms.ModelForm):
    class Meta:
        model = Event
        exclude = ['created_by', 'attendees']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Cata', 'name': 'title'}),
            'description': forms.TextInput(attrs={'placeholder': 'Cata de vino...', 'name': 'description'}),
            'capacity': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '4', 'name': 'capacity'}),
            'min_age': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'años', 'name': 'min_age'}),
            'price': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5€', 'name': 'price'}),
            'location_city': forms.TextInput(attrs={'placeholder': 'Sevilla', 'name': 'location_city'}),
            'location_street': forms.TextInput(attrs={'placeholder': 'Av. Reina Mercerdes', 'name': 'location_street'}),
            'location_number': forms.TextInput(attrs={'placeholder': '01', 'name': 'location_number'}),
            'start_day': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'mm/dd/yyyy', 'name': 'start_day'}),
            'start_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'hh:mm', 'name': 'start_time'}),
            'end_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'hh:mm', 'name': 'end_time'}),
            'pets': forms.Select(choices=CHOICES_YES_NO),
            'lang': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'español', 'name': 'lang'}),
            'parking_nearby': forms.Select(choices=CHOICES_YES_NO),
            'extra_info': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '...', 'name': 'extra_info'}),
        }


class EventUpdateForm(forms.ModelForm):
    class Meta:
        model = Event
        exclude = ['created_by', 'attendees']
        widgets = {
            'title': forms.TextInput(attrs={'name': 'title'}),
            'description': forms.TextInput(attrs={'name': 'description'}),
            'capacity': forms.TextInput(attrs={'class': 'form-control', 'name': 'capacity'}),
            'min_age': forms.TextInput(attrs={'class': 'form-control', 'name': 'min_age'}),
            'price': forms.TextInput(attrs={'class': 'form-control', 'name': 'price'}),
            'location_city': forms.TextInput(attrs={'name': 'location_city'}),
            'location_street': forms.TextInput(attrs={'name': 'location_street'}),
            'location_number': forms.TextInput(attrs={'name': 'location_number'}),
            'start_day': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'mm/dd/yyyy', 'name': 'start_day'}),
            'start_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'hh:mm', 'name': 'start_time'}),
            'end_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'hh:mm', 'name': 'end_time'}),
            'pets': forms.Select(choices=CHOICES_YES_NO),
            'lang': forms.TextInput(attrs={'class': 'form-control', 'name': 'lang'}),
            'parking_nearby': forms.Select(choices=CHOICES_YES_NO),
            'extra_info': forms.TextInput(attrs={'class': 'form-control', 'name': 'extra_info'}),
        }


class LoginForm(AuthenticationForm):
    username = forms.CharField(required=True, widget=forms.TextInput(
        attrs={'placeholder': "usuario"}))
    password = forms.CharField(required=True, widget=forms.PasswordInput(
        attrs={'placeholder': "contraseña"}))

    class Meta:
        model = User
        fields = (
            'username',
            'password',
        )


class RegistrationForm(UserCreationForm):
    username = forms.CharField(required=True, widget=forms.TextInput(
        attrs={'placeholder': "usuario"}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(
        attrs={'placeholder': "email"}))
    birthdate = forms.DateField(required=True, widget=forms.TextInput(
        attrs={'placeholder': "mm/dd/yyyy"}))
    password1 = forms.CharField(required=True, widget=forms.PasswordInput(
        attrs={'placeholder': "contraseña"}))
    password2 = forms.CharField(required=True, widget=forms.PasswordInput(
        attrs={'placeholder': "confirmación contraseña"}))
    friend_token = forms.CharField(required=False, max_length=8, widget=forms.TextInput(
        attrs={'placeholder': "código amigo"}))

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'birthdate',
            'password1',
            'password2',
            'friend_token'
        )

    def clean(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("El email ya existe")
        return self.cleaned_data
