import os
import sys
from pathlib import Path

from gitops.utils.apps import App, get_app_details, get_apps

from .utils.cli import success, warning

__version__ = "0.11.6"


# Checking gitops version matches cluster repo version.
versions_path = Path(os.environ.get("GITOPS_APPS_DIRECTORY", "apps")).parent.absolute() / "setup.cfg"
if versions_path.exists():
    import configparser

    from packaging.version import parse

    config = configparser.RawConfigParser()
    config.read(versions_path)
    if "gitops.versions" in config:
        min_gitops_version = config.get("gitops.versions", "gitops")
        if parse(__version__) < parse(min_gitops_version):
            print(warning("Please upgrade Gitops."), file=sys.stderr)
            print(
                f"Your current version {success(__version__)} is less than the clusters minimum"
                f" requirement {success(min_gitops_version)}.",
                file=sys.stderr,
            )

__all__ = ["App", "get_app_details", "get_apps", "__version__"]
