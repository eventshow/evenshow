import imghdr

from datetime import datetime, date

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserChangeForm, UserCreationForm
from django.contrib.auth.password_validation import password_validators_help_texts
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
    title = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'placeholder': 'Cata', 'name': 'title', 'id': 'title',
               'onkeypress': 'return ValidaLongitud(this, 100);'}))
    description = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'placeholder': 'Cata de vino...', 'name': 'description'}))
    capacity = forms.IntegerField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-eventshow', 'placeholder': '4', 'name': 'capacity'}))
    min_age = forms.IntegerField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-eventshow', 'placeholder': 'años', 'name': 'min_age'}))
    price = forms.DecimalField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-eventshow', 'placeholder': 'precio', 'name': 'min_age'}))
    location_city = forms.CharField(required=False,
                                    widget=forms.TextInput(attrs={'placeholder': 'Sevilla', 'name': 'location_city'}))
    location_street = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'placeholder': 'Av. Reina Mercerdes', 'name': 'location_street'}))
    location_number = forms.CharField(required=False,
                                      widget=forms.TextInput(attrs={'placeholder': '01', 'name': 'location_number'}))
    start_day = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
                                widget=forms.DateInput(format=settings.DATE_INPUT_FORMATS[0],
                                                       attrs={'class': 'form-control', 'placeholder': 'dd/mm/aaaa',
                                                              'name': 'start_day'}))
    start_time = forms.TimeField(required=False, widget=forms.TimeInput(format='%H:%M', attrs={
        'class': 'form-eventshow', 'placeholder': 'hh:mm', 'name': 'start_time'}))
    end_time = forms.TimeField(required=False, widget=forms.TimeInput(format='%H:%M', attrs={
        'class': 'form-eventshow', 'placeholder': 'hh:mm', 'name': 'end_time'}))
    category = forms.ModelChoiceField(Category.objects.all(), empty_label=None)
    picture = forms.ImageField(required=False, widget=forms.ClearableFileInput(
        attrs={'style': 'display: none;'}))

    class Meta:
        model = Event
        exclude = ['created_by', 'attendees']
        extra_info = forms.TextInput(
            attrs={'required': False, 'class': 'form-control', 'name': 'extra_info'})
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Cata', 'name': 'title', 'id': 'title',
                                            'onkeypress': 'return ValidaLongitud(this, 100);'}),
            'description': forms.TextInput(
                attrs={'required': False, 'placeholder': 'Cata de vino...', 'name': 'description'}),
            'capacity': forms.NumberInput(
                attrs={'required': False, 'class': 'form-eventshow', 'placeholder': '4', 'name': 'capacity'}),
            'min_age': forms.NumberInput(
                attrs={'required': False, 'class': 'form-eventshow', 'placeholder': 'años', 'name': 'min_age'}),
            'price': forms.NumberInput(
                attrs={'required': False, 'class': 'form-eventshow', 'placeholder': '5', 'name': 'price'}),
            'location_city': forms.TextInput(
                attrs={'required': False, 'placeholder': 'Sevilla', 'name': 'location_city'}),
            'location_street': forms.TextInput(
                attrs={'required': False, 'placeholder': 'Av. Reina Mercerdes', 'name': 'location_street'}),
            'location_number': forms.TextInput(
                attrs={'required': False, 'placeholder': '01', 'name': 'location_number'}),
            'pets': forms.Select(choices=CHOICES_YES_NO),
            'lang': forms.Select(choices=CHOICES_LANGUAGES),
            'parking_nearby': forms.Select(choices=CHOICES_YES_NO),
            'extra_info': forms.TextInput(
                attrs={'required': False, 'class': 'form-eventshow', 'placeholder': '...', 'name': 'extra_info'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title:
            raise ValidationError('Inserte un título')
        return title

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description:
            raise ValidationError('Inserte una descripción')
        return description

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        if capacity is not None and capacity < 1:
            raise ValidationError(
                'El aforo no puede ser menor que uno')
        elif not capacity and capacity != 0:
            raise ValidationError('Introduzca el aforo')
        return capacity

    def clean_min_age(self):
        min_age = self.cleaned_data.get('min_age')
        if min_age is not None and min_age < 1:
            raise ValidationError(
                'La edad no puede ser menor que uno')
        elif not min_age and min_age != 0:
            raise ValidationError('Introduzca la edad')
        return min_age

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0.0:
            raise ValidationError(
                'El precio no puede ser negativo')
        elif not price and price != 0:
            raise ValidationError('Introduzca el precio')
        return price

    def clean_location_number(self):
        location_city = self.cleaned_data.get('location_city')
        location_street = self.cleaned_data.get('location_street')
        location_number = self.cleaned_data.get('location_number')
        if not location_city or not location_street or not location_number:
            raise ValidationError('Complete la ubicación')
        return location_number

    def clean_start_day(self):
        start_day = self.cleaned_data.get('start_day')
        if not start_day:
            raise ValidationError('Introduzca la fecha')
        return start_day

    def clean_start_time(self):
        start_time = self.cleaned_data.get('start_time')
        if not start_time:
            raise ValidationError('Introduzca la hora de inicio')
        return start_time

    def clean_end_time(self):
        end_time = self.cleaned_data.get('end_time')
        if not end_time:
            raise ValidationError('Inserte la hora de fin')
        return end_time

    def clean_picture(self):
        picture = self.cleaned_data.get('picture')

        if not picture:
            raise ValidationError('Inserte una imagen')
        else:
            if imghdr.what(picture) not in settings.IMAGE_TYPES:
                raise ValidationError(
                    'Formato no soportado, elija entre: JPG, JPEG, PNG')
            if picture.size > 5000000:
                raise ValidationError('El tamaño máximo soportado es de 5 MB')
        return picture

    def clean(self):
        clean_data = self.cleaned_data
        title = self.cleaned_data.get('title')
        description = self.cleaned_data.get('description')
        capacity = self.cleaned_data.get('capacity')
        min_age = self.cleaned_data.get('min_age')
        price = self.cleaned_data.get('price')
        location_city = self.cleaned_data.get('location_city')
        location_street = self.cleaned_data.get('location_street')
        location_number = self.cleaned_data.get('location_number')
        start_day = self.cleaned_data.get('start_day')
        start_time = self.cleaned_data.get('start_time')
        end_time = self.cleaned_data.get('end_time')
        picture = self.cleaned_data.get('picture')
        time1 = datetime.strptime("08:00", "%H:%M").time()

        if isinstance(start_day, type(date)) and (start_day < datetime.now().date() or
                                                  (isinstance(start_time, type(time)) and
                                                   (
                                                      start_day == datetime.now().date() and start_time <= datetime.now().time()))):
            raise ValidationError(
                'El evento no puede comenzar en el pasado')

        if isinstance(start_time, type(time)) and isinstance(end_time, type(time)) and (
                end_time < time1 or start_time < time1):
            raise ValidationError(
                'Este horario no está permitido, más información en los Términos y Condiciones (Horario)')

        if isinstance(start_time, type(time)) and isinstance(end_time, type(time)) and (start_time >= end_time):
            raise ValidationError(
                'El evento no puede empezar después de terminar')


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
        attrs={'placeholder': "contraseña"}), help_text=password_validators_help_texts())
    password2 = forms.CharField(required=True, widget=forms.PasswordInput(
        attrs={'placeholder': "confirmación contraseña"}))
    friend_token = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'placeholder': "código amigo"}))
    terms = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'birthdate',
            'password1',
            'password2',
            'friend_token',
            'terms'
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

    def clean_terms(self):
        terms = self.cleaned_data.get('terms')
        if not terms:
            raise ValidationError(
                'Se deben aceptar los términos y condiciones')
        return terms

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('El usuario es necesario')
        return username


class PasswordUpdateForm(PasswordChangeForm):
    old_password = forms.CharField(required=True, widget=forms.PasswordInput(
        attrs={'placeholder': "antigua contraseña"}))
    new_password1 = forms.CharField(required=True, widget=forms.PasswordInput(
        attrs={'placeholder': "nueva contraseña"}), help_text=password_validators_help_texts())
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
    picture = forms.ImageField(required=False, widget=forms.FileInput(
        attrs={'style': 'display: none;'}))

    class Meta:
        model = Profile
        exclude = ('user',)

    def clean_bio(self):
        bio = self.cleaned_data.get('bio')
        if not bio and self.initial.get('bio'):
            raise ValidationError(
                'Una vez introducido el campo "sobre mí" no se puede dejar en blanco')
        return bio

    def clean_birthdate(self):
        birthdate = self.cleaned_data.get('birthdate')
        if birthdate >= now().date():
            raise ValidationError(
                'La fecha de cumpleaños debe ser en el pasado')
        return birthdate

    def clean_picture(self):
        picture = self.cleaned_data.get('picture', None)
        if picture and imghdr.what(picture) not in settings.IMAGE_TYPES:
            raise ValidationError(
                'Formato no soportado, elija entre: JPG, JPEG, PNG')
        if picture and picture.size > 5000000:
            raise ValidationError('El tamaño máximo soportado es de 5 MB')
        return picture

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
    latitude = forms.DecimalField(required=False, widget=forms.HiddenInput())
    longitude = forms.DecimalField(required=False, widget=forms.HiddenInput())

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

    max_price = forms.DecimalField(min_value=1, decimal_places=2, required=False,
                                   widget=forms.NumberInput(attrs={'placeholder': '€€.€€'}))

    min_price = forms.DecimalField(min_value=0, decimal_places=2, required=False,
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

    def clean_max_price(self):
        max_price = self.cleaned_data.get('max_price')
        if max_price and float(max_price) < 1:
            raise ValidationError(
                'El precio máximo no puede ser menor que 1')
        return max_price

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
