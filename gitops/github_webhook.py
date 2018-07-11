import hashlib
import hmac
import logging
import os
from functools import wraps

from sanic.response import json

logger = logging.getLogger('gitops')


def get_digest(data):
    """ Calculate the digest of a webhook body.

    Uses the environment variable `GITHUB_WEBHOOK_KEY` as the secret hash key.
    """
    return hmac.new(
        os.environ['GITHUB_WEBHOOK_KEY'].encode(),
        data,
        hashlib.sha1
    ).hexdigest()


def github_webhook(view):
    """ Decorator to validate incoming GitHub push webhook.

    Validates the signature using a digest and a secret key. Returns a 400
    error if the digests don't match.
    """
    @wraps(view)
    async def inner(request, *args, **kwargs):
        logger.info('Webhook push recieved.')
        digest = get_digest(request.body)
        signature = request.headers['X-Hub-Signature']
        parts = signature.split('=')
        if not len(parts) == 2 or parts[0] != 'sha1' or \
           not hmac.compare_digest(parts[1], digest):
            logger.info('Invalid digest, aborting.')
            return json({}, status=400)
        logger.info('Valid digest, proceeding.')
        return await view(request, *args, **kwargs)
    return inner
