import os

from .namespace import Namespace


class AppDefinitions:
    def __init__(self, name):
        self.name = name

    def from_path(self, path):
        self.apps = {}
        path = os.path.join(path, 'apps')
        for entry in os.listdir(path):
            entry_path = os.path.join(path, entry)
            if entry[0] != '.' and not os.path.isfile(entry_path):
                app = Namespace(entry, entry_path)
                self.apps[entry] = app
