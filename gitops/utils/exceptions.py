import sys

from .cli import warning


class AppOperationAborted(Exception):
    pass


class AppDoesNotExist(Exception):
    def __init__(self, app_name):
        # Funky hack to stomp on traceback.
        self.args = warning(f"There's no app with the name '{app_name}', silly."),
        sys.exit(self)


class CommandError(Exception):
    pass
