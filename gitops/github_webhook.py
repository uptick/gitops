import hashlib
import hmac
import logging
import os
from functools import wraps

from sanic.response import json

logger = logging.getLogger('gitops')


def get_digest(data):
    return hmac.new(
        os.environ['GITHUB_SECRET'].encode(),
        data,
        hashlib.sha1
    ).hexdigest()


def github_webhook(view):
    @wraps(view)
    async def inner(request, *args, **kwargs):
        logger.info('WEBHOOK RECEIVE')
        digest = get_digest(request.body)
        signature = request.headers['X-Hub-Signature']
        parts = signature.split('=')
        if not len(parts) == 2 or parts[0] != 'sha1' or not hmac.compare_digest(parts[1], digest):
            logger.info('INVALID DIGEST')
            return json({}, status=400)
        return view(request, *args, **kwargs)
    return inner
