import asyncio
import logging

from gitops.deploy import Deployer

logging.basicConfig(level=logging.INFO)

payload = {
    'before': '0e2df044219727927b204061cb8b77b2a19994f4',
    'after': 'a3349eace6f0c8cdea3ba9ffb67f87df8205712d',
    'repository': {
        'clone_url': 'file:///Users/luke/Workspace/uptick/workforce-cluster'
    }
}


async def go():
    deployer = Deployer(payload)
    await deployer.deploy()


loop = asyncio.get_event_loop()
loop.run_until_complete(go())
