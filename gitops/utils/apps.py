from colorama import Fore
from pathlib import Path
from tabulate import tabulate

import gitops.utils.yaml as yaml
from gitops_server.namespace import Namespace

from .cli import colourise, confirm, warning
from .exceptions import AppDoesNotExist, AppOperationAborted
from .images import colour_image
from .tags import colour_tags, validate_tags


def get_app_details(app_name):
    ns = Namespace(app_name)
    try:
        ns.from_path(f'apps/{app_name}')
    except FileNotFoundError:
        raise AppDoesNotExist(app_name)
    values = ns.values
    values['name'] = app_name
    return values


def update_app(app_name, **kwargs):
    filename = Path('apps') / app_name / 'deployment.yml'
    with open(filename, 'r') as f:
        data = yaml.load(f, Loader=yaml.BaseLoader)
    for k, v in kwargs.items():
        if k not in data:
            print(warning(f"Key '{k}' is not a recognised config attribute for {app_name}."))
        data[k] = v
    with open(filename, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)


def get_apps(filter=[], exclude=[], mode='PROMPT', autoexclude_inactive=True, message=None):
    """ Return apps that contain ALL of the tags listed in `filter` and NONE of the tags listed in
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
    if filter == 'all':
        filter = set()
    else:
        filter = set(filter.split(',') if filter and isinstance(filter, str) else filter)
    exclude = set(exclude.split(',') if exclude and isinstance(exclude, str) else exclude)
    if autoexclude_inactive:
        exclude.add('inactive')
    apps = []
    existing_tags = set()
    for entry in sorted(Path('apps').iterdir()):
        if not entry.is_dir():
            continue
        app = get_app_details(entry.name)
        pseudotags = [
            app['name'],
            app['image'].split(':')[-1].split('-')[0],
        ]
        tags = set(app['tags'] + pseudotags)
        existing_tags |= tags
        if filter <= tags and not exclude & tags:
            apps.append(app)

    validate_tags(filter | exclude, existing_tags)

    if mode in ['PROMPT', 'PREVIEW']:
        if mode == 'PROMPT' and message is None:
            message = 'The following apps will be affected:'
        if message is not None:
            print(colourise(f'{message}\n', Fore.LIGHTBLUE_EX))

        preview_apps(apps)

        if mode == 'PROMPT' and not confirm():
            raise AppOperationAborted

    return apps


def preview_apps(apps):
    """ Produce a summary of apps, their tags, and their expected images & replicas.
        May not necessarily reflect actual app statuses if recent changes haven't yet been pushed to
        the remote, or the deployment has failed.
    """
    table = []
    for app in apps:
        table.append([
            colourise(app['name'], Fore.RED, lambda _: 'inactive' in app['tags']),
            colour_image(app.get('image').split(':')[-1]),
            colourise(app.get('containers', {}).get('fg', {}).get('replicas', '-'), Fore.LIGHTBLACK_EX, lambda r: r == '-'),
            colourise(app.get('containers', {}).get('bg', {}).get('replicas', '-'), Fore.LIGHTBLACK_EX, lambda r: r == '-'),
            colour_tags(app['tags']),
        ])
    # Sort table by app tags. TODO: Do we want this over alphabetical app sorting..?
    # table = sorted(table, key=lambda x: x[4])
    print(tabulate(table, ['Name', 'Image', 'FGs', 'BGs', 'Tags']))
