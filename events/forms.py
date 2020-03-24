from datetime import datetime, date

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.timezone import now

from .models import Category, Event, Rating

CHOICES_YES_NO = ((0, "No"), (1, "Sí"))

CHOICES_SCORE = (('--', " "), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5))

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
    start_day = forms.DateField(input_formats=('%d/%m/%Y',),
                                widget=forms.DateInput(format='%d/%m/%Y',
                                                       attrs={'class': 'form-control', 'placeholder': 'dd/mm/aaaa',
                                                              'name': 'start_day'}))

    class Meta:
        model = Event
        exclude = ['created_by', 'attendees']
        extra_info = forms.TextInput(
            attrs={'required': False, 'class': 'form-control', 'name': 'extra_info'})
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Cata', 'name': 'title'}),
            'description': forms.TextInput(attrs={'placeholder': 'Cata de vino...', 'name': 'description'}),
            'picture': forms.TextInput(attrs={'placeholder': 'https://'}),
            'capacity': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '4', 'name': 'capacity'}),
            'min_age': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'años', 'name': 'min_age'}),
            'price': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5€', 'name': 'price'}),
            'location_city': forms.TextInput(attrs={'placeholder': 'Sevilla', 'name': 'location_city'}),
            'location_street': forms.TextInput(attrs={'placeholder': 'Av. Reina Mercerdes', 'name': 'location_street'}),
            'location_number': forms.TextInput(attrs={'placeholder': '01', 'name': 'location_number'}),
            'start_time': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'hh:mm', 'name': 'start_time'}),
            'end_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'hh:mm', 'name': 'end_time'}),
            'pets': forms.Select(choices=CHOICES_YES_NO),
            'lang': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'español', 'name': 'lang'}),
            'parking_nearby': forms.Select(choices=CHOICES_YES_NO),
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
    birthdate = forms.DateField(
        required=True,
        widget=forms.DateInput(
            format='%d/%m/%Y',
            attrs={'placeholder': "dd/mm/aaaa"}
        ),
        input_formats=('%d/%m/%Y',)
    )
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

    def clean_birthdate(self):
        birthdate = self.cleaned_data.get('birthdate')
        if birthdate >= now().date():
            raise ValidationError(
                'La fecha de cumpleaños debe ser en el pasado')
        return birthdate

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('El email ya existe')

        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('El usuario ya existe')
        return username


class SearchHomeForm(forms.Form):
    location = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'placeholder': "Ciudad"}))
    date = forms.DateField(required=False, widget=forms.DateInput(
        attrs={'placeholder': "dd/mm/aaaa"}))
    start_hour = forms.TimeField(required=False, widget=forms.TimeInput(
        attrs={'placeholder': "hh:mm"}))
