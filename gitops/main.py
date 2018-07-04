import logging

from sanic.response import json

from .app import app
from .github_webhook import github_webhook
from .utils import error_handler
from .worker import worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('gitops')


@app.post('/webhook')
@error_handler
@github_webhook
async def webhook(request):
    worker.enqueue(request.json)
    return json({}, status=200)


def main():
    app.run(host='0.0.0.0', port=8000)
