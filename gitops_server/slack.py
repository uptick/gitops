import logging
import os

import aiorequests

logger = logging.getLogger('gitops')


async def post(message):
    """ Post a message to a slack channel

    Uses the environment variable `SLACK_URL` to know which channel to post to.
    This URL is obtained by registering an integration with Slack.
    """
    logger.info('POSTING TO SLACK')
    url = os.environ['SLACK_URL']
    data = {
        'text': message
    }
    async with aiorequests.post(url, data) as response:
        if response.status >= 300:
            logger.error('Failed to post a message to slack (see below):')
            logger.error(f'{message}')
