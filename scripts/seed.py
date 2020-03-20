import csv
import json
import random
import re


from events.models import Category
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core import management
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from faker import Faker

User = get_user_model()

INITIAL_DATA = []

CATEGORIES = ['TV', 'Juegos', 'Idiomas',
              'Aprender', 'Cocina', 'Deportes', 'Otros']
ENROLLMENT_STATUS = ['ACCEPTED', 'PENDING', 'REJECTED']
EVENT_PKS_THIS_YEAR = range(1, 16)
EVENT_PKS_FUTURE = range(16, 31)
PROFILE_IMAGE_FILE = '/static/img/avatar.png'
EVENT_IMAGE_FILE = '/static/img/event.jpg'
FAKE = Faker('es_ES')
USER_PKS = range(1, 51)


def run():
    management.call_command('flush', interactive=False)

    seed_users()
    seed_profiles()
    seed_categories()
    seed_events(FAKE.date_this_year(), EVENT_PKS_THIS_YEAR)
    seed_events(FAKE.date_between(start_date='+1y',
                                  end_date='+2y'), EVENT_PKS_FUTURE)

    with open('initial_data/initial_data.json', 'w') as file:
        file.write(json.dumps(INITIAL_DATA, indent=4))

    management.call_command('loaddata', 'initial_data/initial_data')


def seed_users():
    for pk in USER_PKS:
        profile = FAKE.profile()
        names = profile['name'].split(' ')
        first_name = names[0]
        last_name = names[1]

        fields = {
            'password': make_password(profile['username']),
            'is_superuser': False,
            'username': profile['username'],
            'first_name': first_name,
            'last_name': last_name,
            'email': profile['mail'],
            'is_staff': False,
            'date_joined': now().strftime('%Y-%m-%d %H:%M:%S%z'),
        }
        user = {
            'pk': pk,
            'model': 'auth.User',
            'fields': fields
        }

        INITIAL_DATA.append(user)

    superuser = {
        'pk': USER_PKS[-1]+1,
        'model': 'auth.User',
        'fields': {
            'password': make_password('showman'),
            'is_superuser': True,
            'username': 'showman',
            'is_staff': True,
            'date_joined': now().strftime('%Y-%m-%d %H:%M:%S%z'),
        }
    }

    INITIAL_DATA.append(superuser)


def seed_profiles():
    for user_pk in USER_PKS:
        profile = {
            'pk': user_pk,
            'model': 'events.Profile',
            'fields': {
                'location': FAKE.city(),
                'picture': PROFILE_IMAGE_FILE,
                'birthdate': FAKE.date_of_birth().strftime('%Y-%m-%d'),
                'eventpoints': FAKE.random_int(1, 250),
                'token': get_random_string(length=8).upper(),
                'bio': FAKE.text(),
                'user': user_pk,
            }
        }

        INITIAL_DATA.append(profile)

    superuser_profile = {
        'pk': USER_PKS[-1]+1,
        'model': 'events.Profile',
        'fields': {
            'location': FAKE.city(),
            'picture': PROFILE_IMAGE_FILE,
            'birthdate': FAKE.date_of_birth().strftime('%Y-%m-%d'),
            'token': get_random_string(length=8).upper(),
            'bio': FAKE.text(),
            'user': USER_PKS[-1]+1
        }
    }

    INITIAL_DATA.append(superuser_profile)


def seed_categories():
    for ix, category in enumerate(CATEGORIES):
        fields = {
            'name': category,
        }
        category = {
            'pk': ix,
            'model': 'events.Category',
            'fields': fields
        }
        INITIAL_DATA.append(category)


def seed_events(start_day, event_pks):
    addresses = generate_addresses()
    for event_pk in event_pks:
        category = CATEGORIES.index(random.choice(CATEGORIES))
        host = random.choice(USER_PKS)

        aux = list(USER_PKS).copy()
        aux.remove(host)
        attendees = random.choices(aux, k=6)
        splited_address = FAKE.address().split('\n')
        city = splited_address[1].split(',')[0]

        street = re.match(
            r'[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?(( |\-)[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?)* (((#|[nN][oO]\.?) ?)?(( ?[a-zA-Z\-]+)+)?)',
            splited_address[0]).group()

        # finds all digits in string and take the first which is the street number
        number = [int(s) for s in splited_address[0].split() if s.isdigit()][0]

        address = random.choice(addresses)
        city = address['localidad']
        residence = address['domicilio']
        street = re.match(
            r'[a-zA-ZÀ-ÖØ-öø-ÿ/]+\.?(( |\-)[a-zA-ZÀ-ÖØ-öø-ÿ]+\.?)*',
            residence).group()
        # finds all digits in string and take the first which is the street number
        aux = [int(s) for s in residence.split() if s.isdigit()]
        number = aux[0] if aux else 0
        price = FAKE.random_int(5, 20)

        fields = {
            'title': FAKE.word(),
            'description': FAKE.text(),
            'picture': EVENT_IMAGE_FILE,
            'location_city': city,
            'location_street': street,
            'location_number': number,
            'capacity': FAKE.random_int(2, 20),
            'min_age': FAKE.random_int(16, 25),
            'lang': 'español',
            'pets': random.choice([False, True]),
            'parking_nearby': random.choice([False, True]),
            'extra_info': FAKE.sentence(),
            'start_day': start_day.strftime('%Y-%m-%d'),
            'start_time': FAKE.time() + '+0000',
            'end_time': FAKE.time() + '+0000',
            'price': price,
            'created_by': host,
            'category': category,
        }
        event = {
            'pk': event_pk,
            'model': 'events.Event',
            'fields': fields
        }

        seed_event_enrollments(event_pk, attendees, host, start_day, price)
        if start_day <= now().date():
            seed_event_ratings(event_pk, host, attendees, start_day)

        INITIAL_DATA.append(event)


def generate_addresses():
    data = []

    with open('initial_data/direcciones_dependencias_guardia_civil.csv', encoding='ISO-8859-1') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=';', skipinitialspace=True)
        next(reader)
        for row in reader:
            new = {}
            if row['PROVINCIA'] == 'SEVILLA':
                new['localidad'] = row['LOCALIDAD'].title()
                new['domicilio'] = row['DOMICILIO'].title()

                data.append(new)
    return data


def seed_event_ratings(event, reviewed, reviewers, event_date):
    for reviewer in reviewers:
        on = random.choice(['ATTENDEE', 'HOST'])
        created_at = FAKE.date_time_between(
            start_date=event_date, end_date='+1y').strftime('%Y-%m-%d %H:%M:%S%z')

        fields = {
            'score': FAKE.random_int(1, 5),
            'comment': FAKE.text(),
            'event': event,
            'on': on,
            'created_at': created_at + '+0000',
            'updated_at': created_at + '+0000',
            'created_by': reviewer,
            'reviewed': reviewed,
        }
        rating = {
            'model': 'events.Rating',
            'fields': fields
        }
        INITIAL_DATA.append(rating)


def seed_event_enrollments(event, attendees, host, event_date, price):
    created_at = FAKE.date_time_between(
        start_date='-1y', end_date=event_date)
    updated_at = FAKE.date_time_between(
        start_date=created_at, end_date=event_date).strftime('%Y-%m-%d %H:%M:%S%z')
    created_at = created_at.strftime('%Y-%m-%d %H:%M:%S%z')

    for attendee in attendees:
        status = random.choice(ENROLLMENT_STATUS)

        fields = {
            'status': status,
            'created_at': created_at + '+0000',
            'updated_at': updated_at + '+0000',
            'created_by': attendee,
            'event': event,
        }
        enrollment = {
            'model': 'events.Enrollment',
            'fields': fields
        }

        if status == 'ACCEPTED':
            seed_transaction(attendee, host, updated_at, price)

        INITIAL_DATA.append(enrollment)


def seed_transaction(transmitter, recipient, created_at, amount):
    fields = {
        'amount': amount + 1.15,
        'created_at': created_at + '+0000',
        'updated_at': created_at + '+0000',
        'created_by': transmitter,
        'recipient': recipient,
    }
    transaction = {
        'model': 'events.Transaction',
        'fields': fields
    }

    INITIAL_DATA.append(transaction)
