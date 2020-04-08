from datetime import datetime, date

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.utils.timezone import now


from .models import Category, Event, Profile, Rating

CHOICES_YES_NO = ((False, "No"), (True, "Sí"))

CHOICES_SCORE = (('--', " "), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5))

CHOICES_LANGUAGES = (("ESPAÑOL", "Español"), ("INGLES", "Inglés"), ("MANDARIN", "Mandarín"), ("HINDI", "Hindi"),
                     ("POTUGUES", "Portugués"), ("ARABE", "Árabe"), ("OTROS", "Otros"))

User = get_user_model()

time = datetime.now().time()
date = datetime.now().date()


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
    start_time = forms.TimeField(widget=forms.TimeInput(format='%H:%M', attrs={
                                 'class': 'form-eventshow', 'placeholder': 'hh:mm', 'name': 'start_time'}))
    end_time = forms.TimeField(widget=forms.TimeInput(format='%H:%M', attrs={
                               'class': 'form-eventshow', 'placeholder': 'hh:mm', 'name': 'end_time'}))
    category = forms.ModelChoiceField(Category.objects.all(), empty_label=None)

    class Meta:
        model = Event
        exclude = ['created_by', 'attendees']
        extra_info = forms.TextInput(
            attrs={'required': False, 'class': 'form-control', 'name': 'extra_info'})
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Cata', 'name': 'title', 'id':'title', 'onkeypress': 'return ValidaLongitud(this, 100);'}),
            'description': forms.TextInput(attrs={'required': False, 'placeholder': 'Cata de vino...', 'name': 'description'}),
            'picture': forms.TextInput(attrs={'required': False, 'placeholder': 'https://'}),
            'capacity': forms.NumberInput(attrs={'required': False, 'class': 'form-eventshow', 'placeholder': '4', 'name': 'capacity'}),
            'min_age': forms.NumberInput(attrs={'required': False, 'class': 'form-eventshow', 'placeholder': 'años', 'name': 'min_age'}),
            'price': forms.NumberInput(attrs={'required': False, 'class': 'form-eventshow', 'placeholder': '5', 'name': 'price'}),
            'location_city': forms.TextInput(attrs={'required': False, 'placeholder': 'Sevilla', 'name': 'location_city'}),
            'location_street': forms.TextInput(attrs={'required': False, 'placeholder': 'Av. Reina Mercerdes', 'name': 'location_street'}),
            'location_number': forms.TextInput(attrs={'required': False, 'placeholder': '01', 'name': 'location_number'}),
            'pets': forms.Select(choices=CHOICES_YES_NO),
            'lang': forms.Select(choices=CHOICES_LANGUAGES),
            'parking_nearby': forms.Select(choices=CHOICES_YES_NO),
            'extra_info': forms.TextInput(attrs={'required': False, 'class': 'form-eventshow', 'placeholder': '...', 'name': 'extra_info'}),
        }

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity < 1:
            raise ValidationError(
                'El aforo no puede ser menor que uno')
        return capacity

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price < 0.0:
            raise ValidationError(
                'El precio no puede ser negativo')
        return price

    def clean(self):
        clean_data = self.cleaned_data
        start_day = self.cleaned_data.get('start_day')
        start_time = self.cleaned_data.get('start_time')
        end_time = self.cleaned_data.get('end_time')

        if isinstance(start_day, type(date)) and (start_day < datetime.now().date() or
                                                  (isinstance(start_time, type(time)) and
                                                   (start_day == datetime.now().date() and start_time <= datetime.now().time()))):
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
        attrs={'placeholder': "usuario o email"}))
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
    friend_token = forms.CharField(required=False, widget=forms.TextInput(
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
        if not email:
            raise ValidationError('El email es necesario')
        elif User.objects.filter(email=email).exists():
            raise ValidationError('El email ya existe')
        return email

    def clean_friend_token(self):
        friend_token = self.cleaned_data.get('friend_token')
        deleted_token = Profile.objects.filter(
            user__username='deleted').values('token').first()
        refered = Profile.objects.filter(token=friend_token).exists()

        if friend_token and not refered:
            raise ValidationError('El código introducido no existe')
        elif deleted_token and deleted_token['token'] == friend_token:
            raise ValidationError(';)')
        return friend_token

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('El usuario es necesario')
        return username


class PasswordUpdateForm(PasswordChangeForm):
    old_password = forms.CharField(required=True, widget=forms.PasswordInput(
        attrs={'placeholder': "antigua contraseña"}))
    new_password1 = forms.CharField(required=True, widget=forms.PasswordInput(
        attrs={'placeholder': "nueva contraseña"}))
    new_password2 = forms.CharField(required=True, widget=forms.PasswordInput(
        attrs={'placeholder': "confirmación nueva contraseña"}))

    class Meta:
        model = User
        exclude = ()


class ProfileForm(forms.ModelForm):
    bio = forms.CharField(required=False, widget=forms.Textarea(
        attrs={'placeholder': "bio"}))
    birthdate = forms.DateField(
        required=True,
        widget=forms.DateInput(
            format=settings.DATE_INPUT_FORMATS[0],
            attrs={'placeholder': "dd/mm/aaaa"}
        ),
        input_formats=settings.DATE_INPUT_FORMATS
    )
    location = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'placeholder': "localidad"}))
    picture = forms.URLField(required=False, widget=forms.URLInput(
        attrs={'placeholder': "https://"}))

    class Meta:
        model = Profile
        exclude = ('user',)

    def clean_bio(self):
        bio = self.cleaned_data.get('bio')
        if not bio and self.initial.get('bio'):
            raise ValidationError(
                'Una vez introducida la bio no se puede dejar en blanco')
        return bio

    def clean_birthdate(self):
        birthdate = self.cleaned_data.get('birthdate')
        if birthdate >= now().date():
            raise ValidationError(
                'La fecha de cumpleaños debe ser en el pasado')
        return birthdate

    def save(self, user=None):
        profile = super(ProfileForm, self).save(commit=False)
        if user:
            profile.user = user
        profile.save()
        return profile


class SearchHomeForm(forms.Form):
    location = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'placeholder': "Localidad", 'class': "input-field autocomplete ", 'id': "autocomplete-input"}))
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

    def clean_location(self):
        location = self.cleaned_data.get('location')
        location_join = location.replace(' ', '')
        if not location_join.isalpha() and location:
            raise ValidationError('Introduzca solo letras y espacios')
        return location


class SearchFilterForm(forms.Form):
    location = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'placeholder': "Localidad", 'class': "autocomplete input-field", 'id': "autocomplete-input"}))
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

    max_price = forms.DecimalField(min_value=0.00, decimal_places=2, required=False,
                                   widget=forms.NumberInput(attrs={'placeholder': '€€.€€'}))

    min_price = forms.DecimalField(min_value=0.00, decimal_places=2, required=False,
                                   widget=forms.NumberInput(attrs={'placeholder': '€€.€€'}))

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date < now().date():
            raise ValidationError(
                'La fecha debe ser futura')
        return date

    def clean_location(self):
        location = self.cleaned_data.get('location')
        location_join = location.replace(' ', '')
        if not location_join.isalpha() and location:
            raise ValidationError('Introduzca solo letras y espacios')
        return location

    def clean(self):
        min_price = self.cleaned_data.get('min_price')
        max_price = self.cleaned_data.get('max_price')
        if min_price and max_price and min_price >= max_price:
            raise ValidationError(
                'El precio mínimo no puede ser mayor o igual que el precio máximo')
        return self.cleaned_data


class UserForm(UserChangeForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(
        attrs={'placeholder': "email@email.com"}))
    first_name = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'placeholder': "nombre"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'placeholder': "apellidos"}))

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError('El email es necesario')
        elif User.objects.filter(email=email).exists() and email != self.initial.get('email'):
            raise ValidationError('El email ya existe')
        return email

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name and self.initial.get('first_name'):
            raise ValidationError(
                'Una vez introducido el nombre no se puede dejar en blanco')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name and self.initial.get('last_name'):
            raise ValidationError(
                'Una vez introducido/s los apellido/s no se pueden dejar en blanco')
        return last_name

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('El usuario es necesario')
        return username
