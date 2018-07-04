import asyncio
import logging

from .app import app
from .deploy import Deployer

logger = logging.getLogger('gitops')


class Worker:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def enqueue(self, work):
        logger.info('ENQUEUED WORK, {self.queue.qsize() + 1} IN QUEUE')
        await self.queue.put(work)

    async def run(self):
        while True:
            try:
                await self.process_work()
            except Exception as e:
                logger.error(str(e))

    async def process_work(self):
        work = self.queue.get()
        deployer = Deployer(work)
        deployer.deploy()


worker = Worker()


@app.listener('before_server_start')
async def setup(app, loop):
    worker.task = asyncio.ensure_future(worker.run(), loop=loop)
