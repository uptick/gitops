import asyncio
import logging

from .app import app
from .deploy import Deployer

logger = logging.getLogger('gitops')


class Worker:
    """ Simple syncrhonous background work queue.

    Deployments need to be carried out one at a time to ensure the cluster
    doesn't get confused. The worker is based entirely on asyncio and runs
    alongside the server for maximum efficiency.
    """
    def __init__(self, loop):
        self.loop = loop
        self.queue = asyncio.Queue(loop=self.loop)

    async def enqueue(self, work):
        """ Enqueue an item of work for future processing.

        The `work` argument is the body of an incoming GitHub push webhook.
        """
        logger.info(f'Enqueued work, {self.queue.qsize() + 1} items in the queue.')
        await self.queue.put(work)

    async def run(self):
        """ Run the worker.

        Enters into a loop that waits for work to be queued. Each task is
        awaited here to ensure synchronous operation.
        # TODO: Need to gracefully handle termination.
        """
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
    """ Prepare the worker.

    Creates a new worker object and launches it as a future task.
    """
    global worker
    worker = Worker(loop)
    worker.task = asyncio.ensure_future(worker.run(), loop=loop)
