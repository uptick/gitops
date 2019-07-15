import os

from .namespace import Namespace


class Cluster:
    def __init__(self, name):
        self.name = name

    def from_path(self, path):
        self.namespaces = {}
        path = os.path.join(path, 'apps')
        for entry in os.listdir(path):
            entry_path = os.path.join(path, entry)
            if entry[0] != '.' and not os.path.isfile(entry_path):
                ns = Namespace(entry, entry_path)
                self.namespaces[entry] = ns
