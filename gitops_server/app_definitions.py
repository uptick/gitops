import logging
import os

from common.app import App

from . import ACCOUNT_ID, CLUSTER_NAME

logger = logging.getLogger('gitops')


class AppDefinitions:
    def __init__(self, name):
        self.name = name

    def from_path(self, path):
        self.apps = {}
        path = os.path.join(path, 'apps')
        for entry in os.listdir(path):
            entry_path = os.path.join(path, entry)
            if entry[0] != '.' and not os.path.isfile(entry_path):
                app = App(entry, entry_path, account_id=ACCOUNT_ID)
                # We only care for apps pertaining to our current cluster.
                if app.values['cluster'] == CLUSTER_NAME:
                    self.apps[entry] = app
