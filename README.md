# Eventshow

## Description
Eventshow is a PWA which main in focus is a matchamaking system that puts in touch people looking for an experience they can share with new people in personal residences.

## Requirements
* python 3.8.1
* pip 20.0.2
  * virtualenvwrapper 4.8.4 (optional but useful)
  * django 3.0.4
* npm 6.14.2
* postgresql 12.2-1

(The remaining requirements will specified in **requirements.txt** file)
  
## Config
1. Create a virtual enviroment with `$ python -m venv venv`
    1. virtualenvwrapper (alternative method for creating venvs)
        1. `$ mkvirtualenv eventshow`
        2. `$ workon eventshow`
2. We should first create a new file **settings.py** based on **settings.example.py**, that we should also edit with the appropiate info about the database that we will configure in step 6.
3. Once we got our venv up and running we use pip (inside the venv) to install the requirements with `$(eventshow) pip install -r requirements.txt`.
4. And then we use `$(eventshow) npm install` to install all that is needed for the frontend
5. Create a django superuser with `$ python manage.py createsuperuser'.
6. The next step is to connect to postgres and create a new database and database user with:
    1. `$ sudo -iu postgres`
    2. `[postgres]$ psql -c "create user showman with password 'showman'"`
    3. `[postgres]$ psql -c "create database eventshow owner showman`
7. Then we use `$(eventshow) python manage.py makemigrations` and `$(eventshow) python manage.py migrate` to apply all the migrations to the database.
8. Finally, we use `$python manage.py runscript seed` which will seed/populate the DB and create a superuser with username 'showman' and password 'showman'. Every other user created will have a username 'x' with password 'x'. If the script returns an error like **Can't run script seed** comment the next lines in the **/scripts/seed.py** file:
```
def run():
   ---> management.call_command('flush', interactive=False)

    seed_users()
    seed_profiles()
    seed_categories()
    seed_events(FAKE.date_this_year(), EVENT_PKS_THIS_YEAR)
    seed_events(FAKE.date_between(start_date='+1y',
                                  end_date='+2y'), EVENT_PKS_FUTURE)

    with open('initial_data/initial_data.json', 'w') as file:
        file.write(json.dumps(INITIAL_DATA))

   ---> management.call_command('loaddata', 'initial_data/initial_data')
```
Before you do run the command `$ python manage.py flush` and accept if the command line presents you a confirmation prompt, once you do that run the seeding script and finally, run the following command `$ python manage.py loaddata initial_data/initial_data.json`
