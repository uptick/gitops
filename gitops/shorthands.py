from colorama import Fore
from invoke import task

from .newtenant import create_archiver_ses
from gitops.utils.apps import get_app_details, get_apps
from gitops.utils.cli import colourise, success
from gitops.utils.kube import run_job

from .core import command


@task
def mcommand(ctx, filter, mcommand, exclude='', cleanup=True):
    """ Run django management command on selected app(s).

        eg. inv mcommand customer,sandbox -e aesg showmigrations
    """
    return command(ctx, filter, f'python manage.py {mcommand}', exclude=exclude, cleanup=cleanup)


@task(aliases=['sp'])
def shell_plus(ctx, app, cleanup=True):
    """ Brings up shell_plus for selected app.

        eg. inv sp aesg
    """
    app = get_app_details(app)
    run_job(app, 'python manage.py shell_plus', cleanup=cleanup)
    print(success('Done!'))


@task
def migrate(ctx, filter, exclude='', cleanup=True):
    """ Runs migrations for selected app.

        eg. inv migrate workforce,sandbox
    """
    for app in get_apps(filter=filter, exclude=exclude, mode='PREVIEW', message=f"{colourise('Migrations triggered to run on the following apps:', Fore.LIGHTBLUE_EX)}"):
        run_job(app, 'python manage.py migrate', cleanup=cleanup)
    print(success('Done!'))


@task
def move_to_ses(ctx, filter, exclude='', cleanup=True):
    """ Creates SES mail rules for selected apps.
        Temporary command until we finish migrating existing customers.
    """
    for app in get_apps(filter=filter, exclude=exclude, message=f"{colourise('SES rules to be created on the following apps:', Fore.LIGHTBLUE_EX)}"):
        create_archiver_ses(ctx, name=app["name"], create_legacy_route=True)
    print(success('Done!'))
