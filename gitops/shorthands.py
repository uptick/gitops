import asyncio
from invoke import task

from .core import command
from .utils.apps import get_app_details
from .utils.cli import success
from .utils.kube import run_job

UNSAFE_MANAGE_PY = 'env DJANGO_ALLOW_ASYNC_UNSAFE=true ./manage.py'


@task
def bash(ctx, app, cleanup=True):
    """ Brings up bash shell for selected app.

        eg. inv bash aesg
    """
    app = get_app_details(app)
    asyncio.run(run_job(app, 'bash', cleanup=cleanup))
    print(success('Done!'))


@task
def mcommand(ctx, filter, mcommand, exclude='', cleanup=True, sequential=False, fargate=False):
    """ Run django management command on selected app(s).

        eg. inv mcommand customer,sandbox -e aesg showmigrations
    """
    return command(ctx, filter, f'{UNSAFE_MANAGE_PY} {mcommand}', exclude=exclude, cleanup=cleanup, sequential=sequential, fargate=fargate)


@task(aliases=['sp'])
def shell_plus(ctx, app, cleanup=True):
    """ Brings up shell_plus for selected app.

        eg. inv sp aesg
    """
    app = get_app_details(app)
    asyncio.run(run_job(app, f'{UNSAFE_MANAGE_PY} shell_plus', cleanup=cleanup))
    print(success('Done!'))


@task
def migrate(ctx, filter, exclude='', cleanup=True, sequential=False, interactive=True, fargate=False):
    """ Runs migrations for selected app.

        eg. inv migrate workforce,sandbox
    """
    return command(ctx, filter, f'{UNSAFE_MANAGE_PY} migrate', exclude=exclude, cleanup=cleanup, sequential=sequential, interactive=interactive, fargate=fargate)
