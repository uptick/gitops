from functools import wraps

from sanic.response import json


def error_handler(view):
    """ Decorator to handle view errors.

    Catches any exceptions thrown from a view and encodes them properly. At the
    moment we're capturing any exception and returning it as a string. This
    should be handled more gracefully and also catch more specific errors.
    """
    @wraps(view)
    async def inner(*args, **kwargs):
        try:
            return await view(*args, **kwargs)
        except Exception as e:
            return json({
                'error': e.__class__.__name__,
                'details': str(e)
            }, status=400)
    return inner
