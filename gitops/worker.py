import asyncio
import logging

from .app import app
from .deploy import Deployer

logger = logging.getLogger('gitops')


class Worker:
    def __init__(self, loop):
        self.loop = loop
        self.queue = asyncio.Queue(loop=self.loop)

    async def enqueue(self, work):
        logger.info(f'Enqueued work, {self.queue.qsize() + 1} items in the queue.')
        await self.queue.put(work)

    async def run(self):
        while True:
            try:
                await self.process_work()
            except Exception as e:
                logger.error(str(e))

    async def process_work(self):
        work = await self.queue.get()
        ref = work.get('ref')
        logger.info(f'Have a push to "{ref}".')
        if ref == 'refs/heads/master':
            deployer = Deployer()
            await deployer.from_push_event(work)
            await deployer.deploy()


def get_worker():
    global worker
    return worker


worker = None


@app.listener('before_server_start')
async def setup(app, loop):
    global worker
    worker = Worker(loop)
    worker.task = asyncio.ensure_future(worker.run(), loop=loop)
