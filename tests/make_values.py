import asyncio
import logging

from gitops_server.deploy import Deployer

logging.basicConfig(level=logging.INFO)

payload = {
    'before': 'ddd1f4a49a1898eaf49f5985b5d616d9a0065a1b',
    'after': 'f9b02724b94fa67d8e6cbfd4afb8e9cfeb697969',
    'repository': {
        'clone_url': 'file:///Users/luke/Workspace/uptick/workforce-cluster'
    }
}


async def go():
    deployer = Deployer()
    await deployer.from_push_event(payload)
    await deployer.deploy()


loop = asyncio.get_event_loop()
loop.run_until_complete(go())
