#############
# This code has been pinched from: https://github.com/wimglenn/oyaml/blob/master/oyaml.py
# It tweaks the yaml package to make it preserve ordering when dumping dicts.
#############
import yaml as pyyaml
from collections import OrderedDict


def map_representer(dumper, data):
    return dumper.represent_dict(data.items())


def map_constructor(loader, node):
    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))


# This monkeypatch ensures we get nice indentation for dashed lists.
def increase_indent(self, flow=False, indentless=False):
    return super(pyyaml.dumper.Dumper, self).increase_indent(flow=flow, indentless=False)


if pyyaml.safe_dump is pyyaml.dump:
    # PyYAML v4.1
    SafeDumper = pyyaml.dumper.Dumper
    DangerDumper = pyyaml.dumper.DangerDumper
else:
    SafeDumper = pyyaml.dumper.SafeDumper
    DangerDumper = pyyaml.dumper.Dumper

SafeDumper.increase_indent = increase_indent
DangerDumper.increase_indent = increase_indent

pyyaml.add_representer(dict, map_representer, Dumper=SafeDumper)
pyyaml.add_representer(OrderedDict, map_representer, Dumper=SafeDumper)
pyyaml.add_representer(dict, map_representer, Dumper=DangerDumper)
pyyaml.add_representer(OrderedDict, map_representer, Dumper=DangerDumper)

del map_constructor, map_representer


# Merge PyYAML namespace into ours.
# This allows users a drop-in replacement:
#   import utils.yaml as yaml
from yaml import *  # noqa isort:skip
