import os

from .namespace import Namespace


class Cluster:
    def __init__(self, name):
        self.name = name

    def from_path(self, path):
        self.namespaces = {}
        for entry in os.listdir(path):
            entry_path = os.path.join(path, entry)
            if entry[0] != '.' and not os.path.isfile(entry_path):
                ns = Namespace(entry)
                ns.from_path(entry_path)
                self.namespaces[entry] = ns
