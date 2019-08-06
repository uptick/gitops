import logging

from sanic.response import json

from .app import app
from .github_webhook import github_webhook
from .sanic_utils import error_handler
from .worker import get_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gitops')


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
