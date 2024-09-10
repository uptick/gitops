import asyncio
import logging

from opentelemetry import trace

from .deploy import Deployer

logger = logging.getLogger("gitops_worker")

tracer = trace.get_tracer(__name__)


class DeployQueueWorker:
    """Simple synchronous background work queue.

    Deployments need to be carried out one at a time to ensure the cluster
    doesn't get confused. The worker is based entirely on asyncio and runs
    alongside the server for maximum efficiency.
    """

    _worker = None

    @classmethod
    def get_worker(cls):
        if not cls._worker:
            cls._worker = cls()
        return cls._worker

    def __init__(self):
        self.queue = asyncio.Queue()

    async def enqueue(self, work):
        """Enqueue an item of work for future processing.

        The `work` argument is the body of an incoming GitHub push webhook.
        """
        logger.info(f"Enqueued work, {self.queue.qsize() + 1} items in the queue.")
        await self.queue.put(work)

    async def run(self):
        """Run the worker.

        Enters into a loop that waits for work to be queued. Each task is
        awaited here to ensure synchronous operation.
        # TODO: Need to gracefully handle termination.
        """
        logger.info("Starting up deployer worker loop")
        while True:
            try:
                await self.process_work()
            except Exception as e:
                logger.error(str(e), exc_info=True)

    async def process_work(self):
        work = await self.queue.get()
        ref = work.get("ref")
        logger.info(f'Have a push to "{ref}".')
        if ref == "refs/heads/master":
            with tracer.start_as_current_span("gitops_process_webhook") as current_span:
                deployer = await Deployer.from_push_event(work)
                current_span.set_attribute("gitops.ref", ref)
                current_span.set_attribute("gitops.after", work.get("after"))
                current_span.set_attribute("gitops.before", work.get("before"))
                current_span.set_attribute("gitops.author_email", deployer.author_email)
                current_span.set_attribute("gitops.author_name", deployer.author_name)
                current_span.set_attribute("gitops.commit_message", deployer.commit_message)
                await deployer.deploy()
