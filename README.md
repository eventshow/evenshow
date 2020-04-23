# Eventshow

## Description
Eventshow is a PWA which main in focus is a matchamaking system that puts in touch people looking for an experience they can share with new people in personal residences.

## Requirements
* python 3.8.1
* pip 20.0.2
  * virtualenvwrapper 4.8.4 (optional but useful)
  * django 3.0.4
* postgresql 12.2-1

(The remaining requirements will specified in **requirements.txt** file)

## Config
1. Create a virtual enviroment with `$ python -m venv venv`
    1. virtualenvwrapper (alternative method for creating venvs)
        1. `$ mkvirtualenv eventshow`
        2. `$ workon eventshow`
2. We **MUST** first create a new file **local_settings.py** based on **settings/settings.py**, that we should also edit with the appropiate info about the database that we will configure in step 6.
3. Once we got our venv up and running we use pip (inside the venv) to install the requirements with `$(eventshow) pip install -r requirements.txt`.
4. Create a django superuser with `$ python manage.py createsuperuser'.
5. The next step is to connect to postgres and create a new database and database user with:
    1. `$ sudo -iu postgres`
    2. `[postgres]$ psql -c "create user showman with password 'showman'"`
    3. `[postgres]$ psql -c "create database eventshow owner showman`
    4. (optional) `[postgres]$ psql -c "alter user showman with superuser"`
6. Then we use `$(eventshow) python manage.py makemigrations` and `$(eventshow) python manage.py migrate` to apply all the migrations to the database.
7. Finally, we use `$python manage.py runscript seed` which will seed/populate the DB and create a superuser with username 'showman' and password 'showman'. Every other user created will have a username 'x' with password 'x'. If the script returns an error like **Can't run script seed** comment the next lines in the **/scripts/seed.py** file:
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
Before you do run the command `$ python manage.py flush` and accept if the command line presents you a confirmation prompt, once you do that run the seeding script and finally, run the following command `$ python manage.py loaddata initial_data/initial_data.json`.

## Commits
In order to maintain homogeneity in the commits made to the repository we provide a commit template that enforces good practices. In order to make it default the following steps must be taken:

1. `$ git config commit.template rute/to/the/commit/template`
2. Add the following line to your repo configuration file **.git/config**:
```
[commit]
  template = rute/to/the/commit/template
```
If you are using `Git Desktop` we don't have a solution so keep in mind to check the template (commit_template.txt on the repo root) whenever you are about to make a new commit.

### When to commit? Early and often
A commit should be made in mainly two cases:
- When a unit of work is completed
- When there are changes that may be undone

This means that whenever any of these conditions are met, a commit should be made. If there is work completed a new commit is created (containing only the changes relevant to the particular work, don't git add . /-a), if there are changes that you may want to undo on the future just made another commit for these (you can always use git revert) and use the WIP tag.

### A unit of work
This is not based on time nor type, we consider a unit of work when you have made enough progress to add value/functionality to a new feature. Of course this will depend on the task's context, so please be mindful about when you consider work as finished.

## Branches
We use *Git Flow* so we have a default branch called **dev** to which we make all our *Pull Requests* made from the different branches. These follow a particular naming convention in which we separate the type, department and task code by slashes (/): feat/be|fe/task_code_trello. A branch can have any fo the following names as its first parameter:
- feat/     (new feature)
- fix/      (bug fix)
- hotfix/   (bug fixes during production)
- refactor/ (refactoring code)
- style/    (formatting, missing semi colons, etc; no code change)
- doc/      (changes to documentation)
- test/     (adding or refactoring tests; no production code change)
- release/  (version bump/new release; no production code change)

When a branch is merged into **dev** it will be deleted on the remote repository. You should also delete your local branch with `$ git branch -d branch/name`.

