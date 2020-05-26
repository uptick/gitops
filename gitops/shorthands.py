import asyncio
from invoke import task

from .core import command
from .utils.apps import get_app_details
from .utils.cli import success
from .utils.kube import run_job


@task
def mcommand(ctx, filter, mcommand, exclude='', cleanup=True, sequential=False):
    """ Run django management command on selected app(s).

        eg. inv mcommand customer,sandbox -e aesg showmigrations
    """
    return command(ctx, filter, f'python manage.py {mcommand}', exclude=exclude, cleanup=cleanup, sequential=sequential)


@task(aliases=['sp'])
def shell_plus(ctx, app, cleanup=True):
    """ Brings up shell_plus for selected app.

        eg. inv sp aesg
    """
    app = get_app_details(app)
    asyncio.run(run_job(app, 'python manage.py shell_plus', cleanup=cleanup))
    print(success('Done!'))


@task
def migrate(ctx, filter, exclude='', cleanup=True, sequential=False, interactive=True):
    """ Runs migrations for selected app.

        eg. inv migrate workforce,sandbox
    """
    return command(ctx, filter, f'python manage.py migrate', exclude=exclude, cleanup=cleanup, sequential=sequential, interactive=interactive)
