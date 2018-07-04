import logging
import os
import subprocess
from functools import wraps

import yaml
from sanic.response import json

logger = logging.getLogger('gitops')


def run(command):
    logger.info(f'Running "{command}".')
    exit_code = 0
    try:
        output = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as e:
        exit_code = e.returncode
        output = e.stderr
    return {
        'exit_code': exit_code,
        'output': output
    }


def load_yaml(path, default_value=None):
    try:
        with open(path, 'r') as file:
            return resolve_values(yaml.load(file), path)
    except Exception:
        if default_value is not None:
            return default_value
        raise


def deep_merge(parent, child):
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


def error_handler(view):
    @wraps(view)
    async def inner(*args, **kwargs):
        try:
            return await view(*args, **kwargs)
        except Exception as e:
            return json({
                'error': e.__class__.__name__,
                'details': str(e)
            }, status=400)
    return inner
