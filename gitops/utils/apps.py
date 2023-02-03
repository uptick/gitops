import os
from typing import List, Union

from colorama import Fore
from tabulate import tabulate

from gitops.common.app import DEPLOYMENT_ATTRIBUTES, App
from gitops.settings import get_apps_directory
from gitops.utils import yaml as yaml

from . import get_account_id
from .cli import colourise, confirm, warning
from .exceptions import AppDoesNotExist, AppOperationAborted
from .images import colour_image
from .tags import colour_tags, validate_tags


def get_app_details(app_name: str, load_secrets: bool = True) -> App:
    account_id = get_account_id() if load_secrets else "UNKNOWN"
    try:
        app = App(
            app_name,
            path=get_apps_directory() / app_name,
            load_secrets=load_secrets,
            account_id=account_id,
        )
    except FileNotFoundError:
        # Check if apps dir doesn't exist, or just that one app
        if os.path.exists("apps"):
            raise AppDoesNotExist(app_name)
        else:
            raise AppDoesNotExist()

    return app


def update_app(app_name: str, **kwargs):
    filename = get_apps_directory() / app_name / "deployment.yml"
    with open(filename, "r") as f:
        data = yaml.safe_load(f)
    for k, v in kwargs.items():
        if k not in DEPLOYMENT_ATTRIBUTES:
            print(warning(f"Key '{k}' is not a recognised deployment attribute for {app_name}."))
        if v in [[], {}]:
            if k in data:
                del data[k]
        else:
            data[k] = v
    with open(filename, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def get_apps(
    filter: Union[List[str], str] = "",
    exclude: Union[List[str], str] = "",
    mode="PROMPT",
    autoexclude_inactive=True,
    message=None,
    load_secrets=True,
) -> List[App]:
    """Return apps that contain ALL of the tags listed in `filter` and NONE of the tags listed in
    `exclude`. The incoming filter and exclude params may come in as a list or commastring.
    For the purpose of this filtering, app names and image tag prefixes are also considered as
    tags. For instance, you can do get_apps(tags=[emeriss, production], exclude=[arafire]).
    Calling this method without any args returns all apps.
    There are three modes for communicating selected apps to the user:
    - PROMPT: Prints selected apps and asks for confirmation to proceed.
    - PREVIEW: Prints selected apps then proceeds.
    - SILENT: Proceeds without printing.
    Apps with the `inactive` tag are excluded by default, unless requested otherwise.
    """
    if filter == "all":
        filter = set()
    else:
        filter = set(filter.split(",") if filter and isinstance(filter, str) else filter)

    exclude = set(exclude.split(",") if exclude and isinstance(exclude, str) else exclude)

    if autoexclude_inactive:
        exclude.add("inactive")

    apps = []
    existing_tags = set()

    try:
        directory = sorted(get_apps_directory().iterdir())
    except FileNotFoundError:
        raise AppDoesNotExist()
    for entry in directory:
        if not entry.is_dir():
            continue
        app = get_app_details(entry.name, load_secrets=load_secrets)

        pseudotags = [app.name, app.cluster]
        if app.image and app.image_prefix:
            pseudotags.append(app.image_prefix)

        tags = set(app.tags + pseudotags)
        existing_tags |= tags
        if filter <= tags and not exclude & tags:
            apps.append(app)

    validate_tags(filter | exclude, existing_tags)

    if mode in ["PROMPT", "PREVIEW"]:
        if mode == "PROMPT" and message is None:
            message = "The following apps will be affected:"
        if message is not None:
            print(colourise(f"{message}\n", Fore.LIGHTBLUE_EX))

        preview_apps(apps)

        if mode == "PROMPT" and not confirm():
            raise AppOperationAborted

    return apps


def preview_apps(apps: List[App]):
    """Produce a summary of apps, their tags, and their expected images & replicas.
    May not necessarily reflect actual app statuses if recent changes haven't yet been pushed to
    the remote, or the deployment has failed.
    """
    table = []
    for app in apps:
        table.append(
            [
                colourise(app.name, Fore.RED, lambda _: "inactive" in app.tags),
                colour_image(app.image_tag),
                app.cluster,
                colourise(
                    app.values.get("containers", {}).get("fg", {}).get("replicas", "-"),
                    Fore.LIGHTBLACK_EX,
                    lambda r: r == "-",
                ),
                colourise(
                    app.values.get("containers", {}).get("bg", {}).get("replicas", "-"),
                    Fore.LIGHTBLACK_EX,
                    lambda r: r == "-",
                ),
                colour_tags(app.tags),
            ]
        )
    # Sort table by app tags. TODO: Do we want this over alphabetical app sorting..?
    # table = sorted(table, key=lambda x: x[4])
    print(tabulate(table, ["Name", "Image", "Cluster", "FGs", "BGs", "Tags"]))
