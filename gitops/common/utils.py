import os

import yaml


def load_yaml(path: str) -> dict:
    with open(path) as file:
        return resolve_values(yaml.safe_load(file), path)


def resolve_values(values: dict, path: str) -> dict:
    if "extends" not in values:
        return values
    parent_values = load_yaml(os.path.join(os.path.dirname(path), values["extends"]))
    return deep_merge(parent_values, values)


def deep_merge(parent: dict, child: dict) -> dict:
    """Deeply merge two dictionaries.

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
