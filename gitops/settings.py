import os
from pathlib import Path


def get_apps_directory() -> Path:
    return Path(os.environ.get("GITOPS_APPS_DIRECTORY", "apps"))
