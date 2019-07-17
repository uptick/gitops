import asyncio
import logging
import os
import subprocess
from functools import partial, wraps

import yaml

logger = logging.getLogger('gitops')


async def run(command, catch=False):
    """ Run a shell command.

    Runs the command in an asyncio executor to keep things async. Will
    optionally prevent raising an exception on failure with `catch`. Returns a
    dictionary containing `exit_code` and `output`.
    """
    loop = asyncio.get_event_loop()
    call = partial(
        sync_run,
        command,
        catch=catch
    )
    return await loop.run_in_executor(None, call)


def sync_run(command, catch=False):
    logger.info(f'Running "{command}".')
    exit_code = 0
    try:
        output = subprocess.check_output(
            command,
            shell=True,
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        if not catch:
            raise
        exit_code = e.returncode
        output = e.output
    return {
        'exit_code': exit_code,
        'output': output.decode()
    }


def load_yaml(path, default_value=None):
    try:
        with open(path, 'r') as file:
            return resolve_values(yaml.load(file, Loader=yaml.BaseLoader), path)
    except Exception:
        if default_value is not None:
            return default_value
        raise


def deep_merge(parent, child):
    """ Deeply merge two dictionaries.

    Dictionary entries will be followed and merged, anything else will be
    replaced. If the child dictionary has overlapping values. `child` is merged
    into `parent`. The operation is in-place, but the result is still returned.
    """
    for key, value in child.items():
        parent_value = parent.get(key)
        if isinstance(parent_value, dict):
            if isinstance(value, dict):
                deep_merge(parent_value, value)
            else:
                parent[key] = value
        else:
            parent[key] = value
    return parent


def resolve_values(values, path):
    if 'extends' not in values:
        return values
    parent_values = load_yaml(
        os.path.join(os.path.dirname(path), values['extends'])
    )
    return deep_merge(parent_values, values)


def split_path(path):
    parts = path.split('/')
    if len(parts) == 4 and parts[0].lower() == 'apps':
        namespace = parts[1]
        name = parts[2]
        return namespace, name
    raise ValueError(f'Invalid application path: {path}')
