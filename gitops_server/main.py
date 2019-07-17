import logging

from sanic.response import json

from .app import app
from .github_webhook import github_webhook
from .worker import get_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gitops')



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


@app.post('/webhook')
@error_handler
@github_webhook
async def webhook(request):
    """ Fulfil a git webhook request.

    By this stage the request has been validated and is ready to be queued.
    Return immediately to flag the webhook as received.
    """
    await get_worker().enqueue(request.json)
    return json({}, status=200)


def main():
    app.run(host='0.0.0.0', port=8000)
