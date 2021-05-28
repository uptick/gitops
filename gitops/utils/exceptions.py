import sys

from .cli import warning


class AppOperationAborted(Exception):
    pass


class AppDoesNotExist(Exception):
    def __init__(self, app_name=None):
        # Funky hack to stomp on traceback.
        if app_name:
            message = f"There's no app with the name '{app_name}', silly."
        else:
            message = "Could not find an 'apps' directory. Are you in a cluster repo?"
        self.args = (warning(message),)
        sys.exit(self)


class CommandError(Exception):
    pass
