import asyncio
from invoke import task

from .utils import kube
from .utils.apps import get_app_details
from .utils.cli import progress, warning

# TODO: Abstract this code out of gitops.


#####################
# DATABASE COMMANDS #
#####################
@task
def backup(ctx, app_name):
    """ Backup production or staging database. """
    values = {
        'name': f'{app_name}-backup',
        'app': app_name
    }
    app = get_app_details(app_name, load_secrets=False)
    asyncio.run(kube._run_job('jobs/backup-job.yml', values, context=app['cluster'], namespace='workforce', sequential=True))


@task
def list_backups(ctx, app):
    kube.list_backups('workforce', app)


@task
def restore_backup(ctx, app_name, index):
    """ Restore backed up database. """
    kube.confirm_database(app_name)
    backups = kube.get_backups('workforce', app_name)
    backup = backups[int(index) - 1]
    values = {
        'name': f'{app_name}-restore',
        'timestamp': backup[0],
        'app': app_name,
    }
    app = get_app_details(app_name, load_secrets=False)
    asyncio.run(kube._run_job('jobs/restore-job.yml', values, context=app['cluster'], namespace='workforce'))


@task
def copy_db(ctx, source, destination, skip_backup=False, cleanup=True):
    """ Copy database between apps. """
    kube.confirm_database(destination)
    values = {
        'name': f'copy-db-{source}-{destination}',
        'source': source,
        'destination': destination,
        'skip_backup': 'skip' if skip_backup else ''
    }
    source_app = get_app_details(source, load_secrets=False)
    destination_app = get_app_details(destination, load_secrets=False)
    if source_app['cluster'] != destination_app['cluster']:
        print(warning(f"Source ({source!r} on {source_app['cluster']!r}) and destination ({destination!r} on {destination_app['cluster']!r}) apps must belong to the same cluster."))
        return
    asyncio.run(kube._run_job('jobs/copy-db-job.yml', values, context=source_app['cluster'], namespace='workforce', cleanup=cleanup))
    print(progress('You may want to clear the redis cache now!'))
    print(progress(f'\t- gitops mcommand {destination} clear_cache'))


@task
def download_backup(ctx, app, index, path=None, datestamp=False):
    """ Download production or staging backup. """
    kube.download_backup('workforce', app, index, path, datestamp=datestamp)
