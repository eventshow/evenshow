from datetime import datetime, date

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.timezone import now

from .models import Category, Event, Rating

CHOICES_YES_NO = ((0, "No"), (1, "Sí"))

CHOICES_SCORE = (('--', " "), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5))

User = get_user_model()

time = now().time()


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        exclude = ['event', 'on', 'created_by', 'reviewed']
        widgets = {
            'score': forms.Select(choices=CHOICES_SCORE),
            'comment': forms.Textarea(attrs={'placeholder': '-'}),
        }


class EventForm(forms.ModelForm):
    start_day = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS,
                                widget=forms.DateInput(format=settings.DATE_INPUT_FORMATS[0],
                                                       attrs={'class': 'form-control', 'placeholder': 'dd/mm/aaaa',
                                                              'name': 'start_day'}))
    start_time = forms.TimeField(widget=forms.TimeInput(format='%H:%M', attrs={'class': 'form-eventshow', 'placeholder': 'hh:mm', 'name': 'start_time'}))
    end_time = forms.TimeField(widget=forms.TimeInput(format='%H:%M', attrs={'class': 'form-eventshow', 'placeholder': 'hh:mm', 'name': 'end_time'}))
    category = forms.ModelChoiceField(Category.objects.all(), empty_label=None)


    class Meta:
        model = Event
        exclude = ['created_by', 'attendees']
        extra_info = forms.TextInput(
            attrs={'required': False, 'class': 'form-control', 'name': 'extra_info'})
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Cata', 'name': 'title'}),
            'description': forms.TextInput(attrs={'placeholder': 'Cata de vino...', 'name': 'description'}),
            'picture': forms.TextInput(attrs={'placeholder': 'https://'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-eventshow', 'placeholder': '4', 'name': 'capacity'}),
            'min_age': forms.NumberInput(attrs={'class': 'form-eventshow', 'placeholder': 'años', 'name': 'min_age'}),
            'price': forms.NumberInput(attrs={'class': 'form-eventshow', 'placeholder': '5', 'name': 'price'}),
            'location_city': forms.TextInput(attrs={'placeholder': 'Sevilla', 'name': 'location_city'}),
            'location_street': forms.TextInput(attrs={'placeholder': 'Av. Reina Mercerdes', 'name': 'location_street'}),
            'location_number': forms.TextInput(attrs={'placeholder': '01', 'name': 'location_number'}),
            'start_day': forms.DateInput(attrs={'class': 'form-eventshow', 'placeholder': 'dd/mm/yyyy', 'name': 'start_day'}),
            'pets': forms.Select(choices=CHOICES_YES_NO),
            'lang': forms.TextInput(attrs={'class': 'form-eventshow', 'placeholder': 'español', 'name': 'lang'}),
            'parking_nearby': forms.Select(choices=CHOICES_YES_NO),
            'extra_info': forms.TextInput(attrs={'class': 'form-eventshow', 'placeholder': '...', 'name': 'extra_info'}),
        }



    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity < 1:
            raise ValidationError(
                'El aforo no puede ser menor que uno')
        return capacity
    
    def clean(self):
        clean_data = self.cleaned_data
        start_day = self.cleaned_data.get('start_day')
        start_time = self.cleaned_data.get('start_time')
        end_time = self.cleaned_data.get('end_time')

        if (start_day < now().date()):
            raise ValidationError(
                'El evento no puede comenzar en el pasado')
        elif isinstance(start_time, type(time)) and (start_day == now().date() and start_time <= now().time()):
                raise ValidationError(
                    'El evento no puede comenzar en el pasado')

        
        if not isinstance(start_time, type(time)): 
            raise ValidationError('Inserte una hora')
        elif isinstance(end_time, type(time)) and (start_time >= end_time):
                raise ValidationError(
                    'El evento no puede empezar después de terminar')
        return clean_data

    def clean_end_time(self):
        end_time = self.cleaned_data.get('end_time')
        if not isinstance(end_time, type(time)): 
            raise ValidationError('Inserte una hora')
        return end_time


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
            format=settings.DATE_INPUT_FORMATS[0],
            attrs={'placeholder': "dd/mm/aaaa"}
        ),
        input_formats=settings.DATE_INPUT_FORMATS
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
        attrs={'placeholder': "Localidad"}))
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            format=settings.DATE_INPUT_FORMATS[0],
            attrs={'placeholder': "dd/mm/aaaa"}
        ),
        input_formats=settings.DATE_INPUT_FORMATS
    )
    start_hour = forms.TimeField(
        required=False,
        widget=forms.TimeInput(
            format='%H:%M',
            attrs={'placeholder': "hh:mm"}
        ),
        input_formats=('%H:%M',)
    )

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date < now().date():
            raise ValidationError(
                'La fecha debe ser futura')
        return date
