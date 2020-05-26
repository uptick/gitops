import asyncio
from colorama import Fore
from invoke import run, task

from .utils.apps import get_apps, update_app
from .utils.async_runner import run_tasks_async_with_progress
from .utils.cli import colourise, progress, success, success_negative, warning
from .utils.exceptions import AppOperationAborted
from .utils.images import colour_image, get_image, get_latest_image
from .utils.kube import run_job
from .utils.tags import colour_tag, sort_tags


@task
def summary(ctx, filter='', exclude=''):
    """ Produce a summary of apps, their tags, and their expected images & replicas.
        May not necessarily reflect actual app statuses if recent changes haven't yet been pushed to
        the remote, or the deployment has failed.
    """
    get_apps(filter=filter, exclude=exclude, mode='PREVIEW', autoexclude_inactive=False, load_secrets=False)


@task
def bump(ctx, filter, exclude='', image_tag=None, prefix=None, autoexclude_inactive=True, interactive=True):
    """ Bump image tag on selected app(s).
        Provide `image_tag` to set to a specific image tag, or provide `prefix` to use latest image
        with the given prefix.
        Otherwise, the latest tag with the same prefix as the app's current tag will be used.
    """
    prompt_message = 'The following apps will have their image bumped'
    if image_tag:
        prompt_message += f' to use {colourise(image_tag, Fore.LIGHTYELLOW_EX)}'
    if prefix:
        prompt_message += f' to use prefix {colourise(prefix, Fore.LIGHTYELLOW_EX)}'
    try:
        apps = get_apps(
            filter=filter,
            exclude=exclude,
            autoexclude_inactive=autoexclude_inactive,
            message=f"{prompt_message}{colourise(':', Fore.LIGHTBLUE_EX)}",
            load_secrets=False,
            mode='PROMPT' if interactive else 'SILENT',
        )
    except AppOperationAborted:
        print(success_negative('Aborted.'))
        return
    for app in apps:
        app_name = app['name']
        prev_image_tag = app['image-tag']
        if image_tag is None:
            if prefix is None:
                new_image_prefix = prev_image_tag.split('-')[0]
            else:
                new_image_prefix = prefix
            new_image_tag = get_latest_image(new_image_prefix)
        else:
            new_image_tag = get_image(image_tag)
        if new_image_tag != prev_image_tag:
            print(f"Bumping {colourise(app_name, Fore.LIGHTGREEN_EX)}: {colour_image(prev_image_tag)} -> {colour_image(new_image_tag)}")
            update_app(app_name, **{'image-tag': new_image_tag})
        else:
            print(f"Skipping {colourise(app_name, Fore.LIGHTGREEN_EX)}: already on {colour_image(new_image_tag)}")
    commit_message = f"Bump {filter}"
    if exclude:
        commit_message += f" (except {exclude})"
    if image_tag:
        commit_message += f" to use {image_tag}"
    if prefix:
        commit_message += f" to use prefix {prefix}"
    run(f'git commit -am "{commit_message}."')
    print(success('Done!'))


@task
def command(ctx, filter, command, exclude='', cleanup=True, sequential=True, interactive=True):
    """ Run command on selected app(s).

        eg. inv command customer,sandbox -e aesg "python manage.py migrate"
    """
    try:
        apps = get_apps(
            filter=filter,
            exclude=exclude,
            message=f"{colourise('The command', Fore.LIGHTBLUE_EX)} {colourise(command, Fore.LIGHTYELLOW_EX)} {colourise('will be run on the following apps:', Fore.LIGHTBLUE_EX)}",
            mode='PROMPT' if interactive else 'SILENT',
        )
    except AppOperationAborted:
        print(success_negative('Aborted.'))
        return

    # async output is by nature interactive
    if sequential or (not interactive) or len(apps) == 1:
        for app in apps:
            # For each app, just run the coroutine and print the output
            print(asyncio.run(run_job(app, command, cleanup=cleanup, sequential=sequential)))
    else:
        # Build list of coroutines, and execute them all at once
        jobs = [(run_job(app, command, cleanup=cleanup, sequential=sequential), app['name']) for app in apps]
        asyncio.run(run_tasks_async_with_progress(jobs))

    print(success('Done!'))


@task
def tag(ctx, filter, tag, exclude=''):
    """ Set a tag on selected app(s). """
    try:
        apps = get_apps(
            filter=filter,
            exclude=exclude,
            autoexclude_inactive=False,
            message=f"{colourise('The tag', Fore.LIGHTBLUE_EX)} {colour_tag(tag)} {colourise('will be added to the following apps:', Fore.LIGHTBLUE_EX)}",
            load_secrets=False,
        )
    except AppOperationAborted:
        print(success_negative('Aborted.'))
        return
    for app in apps:
        update_app(app['name'], tags=sort_tags(set(app['tags']) | {tag}))
    commit_message = f"Add tag '{tag}' to {filter}"
    if exclude:
        commit_message += f" (except {exclude})"
    run(f'git commit -am "{commit_message}."')
    print(success('Done!'))


@task
def untag(ctx, filter, tag, exclude=''):
    """ Unset a tag from selected app(s). """
    try:
        apps = get_apps(
            filter=filter,
            exclude=exclude,
            autoexclude_inactive=False,
            message=f"{colourise('The tag', Fore.LIGHTBLUE_EX)} {colour_tag(tag)} {colourise('will be removed from the following apps:', Fore.LIGHTBLUE_EX)}",
            load_secrets=False,
        )
    except AppOperationAborted:
        print(success_negative('Aborted.'))
        return
    for app in apps:
        update_app(app['name'], tags=sort_tags(set(app['tags']) - {tag}))
    commit_message = f"Remove tag '{tag}' from {filter}"
    if exclude:
        commit_message += f" (except {exclude})"
    run(f'git commit -am "{commit_message}."')
    print(success('Done!'))


@task
def getenv(ctx, filter, exclude='', keys='', **kwargs):
    """ Get one or more env vars on selected app(s).
    """
    _getenv('environment', filter, exclude, keys, **kwargs)


@task
def getsecrets(ctx, filter, exclude='', keys='', **kwargs):
    """ Get one or more secrets on selected app(s).
    """
    _getenv('secrets', filter, exclude, keys, **kwargs)


def _getenv(value_type, filter, exclude, filter_values, **kwargs):
    filter_values = filter_values.split(',') if filter_values else ''
    apps = get_apps(filter=filter, exclude=exclude, mode='SILENT')
    for app in apps:
        print('-' * 20, progress(app['name']), sep='\n')
        values = app.get(value_type)
        if type(values) == dict:
            filtered_values = {k: v for k, v in values.items() if k in filter_values} if filter_values else values
            for k, v in filtered_values.items():
                print(f"{k}={v}")
        else:
            print(warning(f'No {value_type} set.'))


@task
def setenv(ctx, filter, exclude='', **kwargs):
    """ Set one or more env vars on selected app(s).
        However, please make more broad-reaching environment changes at the chart level though.
    """
    # TODO: FINISH THIS - get kwargs coming in from invoke.
    raise NotImplementedError
    try:
        apps = get_apps(filter=filter, exclude=exclude, message=f"{colourise('The env var(s)', Fore.LIGHTBLUE_EX)}\n{colourise(kwargs, Fore.LIGHTYELLOW_EX)}\n{colourise('will be added to the following apps:', Fore.LIGHTBLUE_EX)}")
    except AppOperationAborted:
        print(success_negative('Aborted.'))
        return
    for app in apps:
        update_app(app['name'], environment={**app['environment'], **kwargs})
    print(success('Done!'))


@task
def unsetenv(ctx, filter, exclude='', **kwargs):
    """ Clears one or more env vars on selected app(s).
        However, please make more broad-reaching environment changes at the chart level though.
    """
    # TODO: FINISH THIS - get kwargs coming in from invoke.
    raise NotImplementedError
    try:
        apps = get_apps(filter=filter, exclude=exclude, message=f"{colourise('The env var(s)', Fore.LIGHTBLUE_EX)}\n{colourise(kwargs, Fore.LIGHTYELLOW_EX)}\n{colourise('will be removed from the following apps:', Fore.LIGHTBLUE_EX)}")
    except AppOperationAborted:
        print(success_negative('Aborted.'))
        return
    for app in apps:
        environment = app['environment']
        for k in kwargs:
            del app[k]
        update_app(app['name'], environment={environment})
    print(success('Done!'))
