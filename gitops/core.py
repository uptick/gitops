import asyncio
import uuid

from colorama import Fore
from invoke import run, task

from .settings import get_apps_directory
from .utils import config
from .utils.apps import get_apps, update_app
from .utils.async_runner import run_tasks_async_with_progress
from .utils.cli import colourise, progress, success, success_negative, warning
from .utils.exceptions import AppOperationAborted
from .utils.images import colour_image, get_image, get_latest_image
from .utils.kube import run_job
from .utils.tags import colour_tag, sort_tags


@task
def summary(ctx, filter="", exclude=""):
    """Produce a summary of apps, their tags, and their expected images & replicas.
    May not necessarily reflect actual app statuses if recent changes haven't yet been pushed to
    the remote, or the deployment has failed.
    """
    get_apps(
        filter=filter,
        exclude=exclude,
        mode="PREVIEW",
        autoexclude_inactive=False,
        load_secrets=False,
    )


@task
def bump(
    ctx,
    filter,
    exclude="",
    image_tag=None,
    prefix=None,
    autoexclude_inactive=True,
    interactive=True,
    push=False,
    redeploy=False,
    skip_migrations=False,
):
    """Bump image tag on selected app(s).
    Provide `image_tag` to set to a specific image tag, or provide `prefix` to use latest image
    with the given prefix.
    Otherwise, the latest tag with the same prefix as the app's current tag will be used.
    Provide `push` to automatically push the commit (and retry on conflict.)
    Provide `redeploy` to redeploy servers even if nothing has changed.
    Provide `skip_migrations` to disable running migrations via helm hooks.
    """
    prompt_message = "The following apps will have their image bumped"
    if image_tag:
        prompt_message += f" to use {colourise(image_tag, Fore.LIGHTYELLOW_EX)}"
    if prefix:
        prompt_message += f" to use prefix {colourise(prefix, Fore.LIGHTYELLOW_EX)}"
    try:
        apps = get_apps(
            filter=filter,
            exclude=exclude,
            autoexclude_inactive=autoexclude_inactive,
            message=f"{prompt_message}{colourise(':', Fore.LIGHTBLUE_EX)}",
            load_secrets=False,
            mode="PROMPT" if interactive else "SILENT",
        )
    except AppOperationAborted:
        print(success_negative("Aborted."))
        return

    if push:
        run(f"cd {get_apps_directory()}; git pull")

    for app in apps:
        app_name = app.name
        prev_image_tag = app.image_tag
        if image_tag is None:
            # if we haven't specified a prefix
            if prefix is None:
                new_image_prefix = app.image_prefix
            else:
                new_image_prefix = prefix
            new_image_tag = get_latest_image(app.image_repository_name, new_image_prefix)
        else:
            new_image_tag = get_image(image_tag)

        if not new_image_tag:
            print(
                f"Skipping {colourise(app_name, Fore.LIGHTRED_EX)}: no image matching"
                f" {colour_image(new_image_tag)}"
            )
        elif new_image_tag != prev_image_tag:
            print(
                f"Bumping {colourise(app_name, Fore.LIGHTGREEN_EX)}: {colour_image(prev_image_tag)}"
                f" -> {colour_image(new_image_tag)}"
            )
            update_app(app_name, **{"image-tag": new_image_tag})
        elif redeploy:
            print(f"Redeploying {colourise(app_name, Fore.LIGHTGREEN_EX)}")
            update_app(app_name, **{"bump": str(uuid.uuid4())})
        else:
            print(
                f"Skipping {colourise(app_name, Fore.LIGHTGREEN_EX)}: already on"
                f" {colour_image(new_image_tag)}"
            )
    if redeploy:
        commit_message = f"Redeploying {filter}"
    else:
        commit_message = f"Bump {filter}"

    if exclude:
        commit_message += f" (except {exclude})"
    if image_tag:
        commit_message += f" to use {image_tag}"
    if prefix:
        commit_message += f" to use prefix {prefix}"
    if skip_migrations:
        commit_message += " --skip-migrations"

    run(f'cd {get_apps_directory()}; git commit -am "{commit_message}."')

    if push:
        git_push(get_apps_directory())

    print(success("Done!"))


@task
def command(
    ctx,
    filter,
    command,
    exclude="",
    cleanup=True,
    sequential=True,
    interactive=True,
    cpu=0,
    memory=0,
):
    """Run command on selected app(s).

    eg. inv command customer,sandbox -e aesg "python manage.py migrate"
    """
    try:
        apps = get_apps(
            filter=filter,
            exclude=exclude,
            message=(
                f"{colourise('The command', Fore.LIGHTBLUE_EX)}"
                f" {colourise(command, Fore.LIGHTYELLOW_EX)}"
                f" {colourise('will be run on the following apps:', Fore.LIGHTBLUE_EX)}"
            ),
            mode="PROMPT" if interactive else "SILENT",
        )
    except AppOperationAborted:
        print(success_negative("Aborted."))
        return

    # async output is by nature interactive
    if sequential or (not interactive) or len(apps) == 1:
        for app in apps:
            # For each app, just run the coroutine and print the output
            print(
                asyncio.run(
                    run_job(app, command, cleanup=cleanup, sequential=True, cpu=cpu, memory=memory)
                )
            )
    else:
        # Build list of coroutines, and execute them all at once
        jobs = [
            (
                run_job(
                    app, command, cleanup=cleanup, sequential=sequential, cpu=cpu, memory=memory
                ),
                app.name,
            )
            for app in apps
        ]
        asyncio.run(run_tasks_async_with_progress(jobs, max_concurrency=10))

    print(success("Done!"))


@task
def tag(ctx, filter, tag, exclude=""):
    """Set a tag on selected app(s)."""
    try:
        apps = get_apps(
            filter=filter,
            exclude=exclude,
            autoexclude_inactive=False,
            message=(
                f"{colourise('The tag', Fore.LIGHTBLUE_EX)} {colour_tag(tag)}"
                f" {colourise('will be added to the following apps:', Fore.LIGHTBLUE_EX)}"
            ),
            load_secrets=False,
        )
    except AppOperationAborted:
        print(success_negative("Aborted."))
        return
    for app in apps:
        update_app(app.name, tags=sort_tags(set(app.tags) | {tag}))
    commit_message = f"Add tag '{tag}' to {filter}"
    if exclude:
        commit_message += f" (except {exclude})"
    run(f'git commit -am "{commit_message}."')
    print(success("Done!"))


@task
def untag(ctx, filter, tag, exclude=""):
    """Unset a tag from selected app(s)."""
    try:
        apps = get_apps(
            filter=filter,
            exclude=exclude,
            autoexclude_inactive=False,
            message=(
                f"{colourise('The tag', Fore.LIGHTBLUE_EX)} {colour_tag(tag)}"
                f" {colourise('will be removed from the following apps:', Fore.LIGHTBLUE_EX)}"
            ),
            load_secrets=False,
        )
    except AppOperationAborted:
        print(success_negative("Aborted."))
        return
    for app in apps:
        update_app(app.name, tags=sort_tags(set(app.tags) - {tag}))
    commit_message = f"Remove tag '{tag}' from {filter}"
    if exclude:
        commit_message += f" (except {exclude})"
    run(f'git commit -am "{commit_message}."')
    print(success("Done!"))


@task  # TODO: want `keys` to be optional-positional: https://github.com/pyinvoke/invoke/issues/159
def getenv(ctx, filter, keys="", exclude=""):
    """Get one or more env vars on selected app(s)."""
    _getenv("environment", filter, exclude, keys)


@task  # TODO: want `keys` to be optional-positional: https://github.com/pyinvoke/invoke/issues/159
def getsecrets(ctx, filter, keys="", exclude=""):
    """Get one or more secrets on selected app(s)."""
    _getenv("secrets", filter, exclude, keys)


def _getenv(env_or_secrets, filter, exclude, filter_values):
    filter_values = filter_values.split(",") if filter_values else ""
    apps = get_apps(filter=filter, exclude=exclude, mode="SILENT")
    for app in apps:
        print("-" * 20, progress(app.name), sep="\n")
        values = app.values.get(env_or_secrets)
        if type(values) == dict:
            filtered_values = (
                {k: v for k, v in values.items() if k in filter_values} if filter_values else values
            )
            for k, v in filtered_values.items():
                print(f"{k}={v}")
        else:
            print(warning(f"No {env_or_secrets} set."))


def _sort_envs(envs):
    sorted_envs = {}
    for e in config.getlist("env_order", fallback=""):
        if e in envs:
            sorted_envs[e] = envs.pop(e)
    for e in sorted(envs):
        sorted_envs[e] = envs[e]
    return sorted_envs


@task
def setenv(ctx, filter, values, exclude=""):
    """Set one or more env vars on selected app(s).

    eg. inv setenv customer,sandbox BG_RUNNER=DRAMATIQ,BUMP=2

    NOTE: More broad-reaching environment changes should be made at the chart level.
    """
    splitenvs = values.split(",")  # pardon the pun.
    formatted_splitenvs = "\n".join(splitenvs)
    try:
        apps = get_apps(
            filter=filter,
            exclude=exclude,
            message=(
                f"{colourise('The env var(s)', Fore.LIGHTBLUE_EX)}\n{colourise(formatted_splitenvs, Fore.LIGHTYELLOW_EX)}\n{colourise('will be added to the following apps:', Fore.LIGHTBLUE_EX)}"
            ),
        )
    except AppOperationAborted:
        print(success_negative("Aborted."))
        return
    for app in apps:
        update_app(
            app.name,
            environment=_sort_envs(
                {
                    **dict(tuple(e.split("=")) for e in splitenvs),
                    **app.values.get("environment", {}),
                }
            ),
        )
    commit_message = f"Set env var(s) '{values}' on {filter}"
    if exclude:
        commit_message += f" (except {exclude})"
    run(f'git commit -am "{commit_message}."')
    print(success("Done!"))


@task
def unsetenv(ctx, filter, values, exclude=""):
    """Unset one or more env vars on selected app(s).

    eg. inv unsetenv customer,sandbox BG_RUNNER,BUMP

    NOTE: More broad-reaching environment changes should be made at the chart level.
    """
    splitenvs = values.split(",")  # pardon the pun.
    formatted_splitenvs = "\n".join(splitenvs)
    try:
        apps = get_apps(
            filter=filter,
            exclude=exclude,
            message=(
                f"{colourise('The env var(s)', Fore.LIGHTBLUE_EX)}\n{colourise(formatted_splitenvs, Fore.LIGHTYELLOW_EX)}\n{colourise('will be removed from the following apps:', Fore.LIGHTBLUE_EX)}"
            ),
        )
    except AppOperationAborted:
        print(success_negative("Aborted."))
        return
    for app in apps:
        environment = app.values.get("environment", {})
        for e in splitenvs:
            if e in environment:
                del environment[e]
        update_app(app.name, environment=_sort_envs(environment))
    commit_message = f"Unset env var(s) '{values}' on {filter}"
    if exclude:
        commit_message += f" (except {exclude})"
    run(f'git commit -am "{commit_message}."')
    print(success("Done!"))


@task
def setcluster(ctx, filter, cluster, exclude=""):
    """Move selected app(s) to given cluster.

    eg. inv setcluster customer,sandbox eks-prod
    """
    try:
        apps = get_apps(
            filter=filter,
            exclude=exclude,
            message=(
                f"{colourise('The following apps will be moved to the', Fore.LIGHTBLUE_EX)}"
                f" {colourise(cluster, Fore.LIGHTYELLOW_EX)}"
                f" {colourise('cluster:', Fore.LIGHTBLUE_EX)}"
            ),
        )
    except AppOperationAborted:
        print(success_negative("Aborted."))
        return
    for app in apps:
        update_app(app.name, cluster=cluster)
    commit_message = f"Move {filter} to cluster '{cluster}'"
    if exclude:
        commit_message += f" (except {exclude})"
    run(f'git commit -am "{commit_message}."')
    print(success("Done!"))


def git_push(cluster_path: str, retry: int = 3):
    """Git pushes in a directory and retries if commits already exist"""
    print(progress(f"Pushing changes to {cluster_path}"))
    attempts = 0
    while attempts <= retry:
        result = run(f"cd {cluster_path}; git push", warn=True)
        if result.exited == 1 and "remote contains work" in result.stderr:
            attempts += 1
            run(f"cd {cluster_path}; git pull --rebase=true")
        else:
            break
