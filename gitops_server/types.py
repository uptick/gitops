import logging
import os
from typing import TypedDict

from gitops.common.app import App
from gitops_server import settings

logger = logging.getLogger("gitops")


class RunOutput(TypedDict):
    exit_code: int
    output: str


class UpdateAppResult(RunOutput):
    app_name: str
    slack_message: str


class AppDefinitions:
    def __init__(self, name, apps: dict[str, App] | None = None, path: str | None = None):
        self.name = name
        self.apps = apps or {}

        if path:
            path = os.path.join(path, "apps")

            for entry in os.listdir(path):
                entry_path = os.path.join(path, entry)
                if entry[0] != "." and not os.path.isfile(entry_path):
                    app = App(entry, entry_path, account_id=settings.ACCOUNT_ID)
                    self.apps[entry] = app

        # Removing apps that are suspended or not part of this cluster
        for app in list(self.apps.values()):
            # We only care for apps pertaining to our current cluster.
            if app.values["cluster"] != settings.CLUSTER_NAME or "suspended" in app.tags:
                # and suspended apps are considered removed from the cluster.
                self.apps.pop(app.name)
