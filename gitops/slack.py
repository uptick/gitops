import logging
import os

import aiorequests

logger = logging.getLogger('gitops')


async def post(message):
    logger.info('POSTING TO SLACK')
    url = os.environ['SLACK_URL']
    data = {
        'text': message
    }
    async with aiorequests.post(url, data) as response:
        if response.status >= 300:
            logger.error('FILED TO POST TO SLACK')
