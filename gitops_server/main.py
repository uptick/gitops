import asyncio
import hashlib
import hmac
import logging

from fastapi import HTTPException, Request

from gitops_server import settings
from gitops_server.app import app
from gitops_server.deployment_checker import DeploymentStatusWorker
from gitops_server.logging_config import *  # noqa
from gitops_server.worker import Worker  # noqa

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gitops")


@app.get("/")
def index():
    return {}


@app.post("/webhook")
async def webhook(request: Request):
    """Fulfil a git webhook request"""
    digest = get_digest(await request.body())
    signature = request.headers["X-Hub-Signature"]

    validate_signature(signature, digest)

    json = await request.json()

    worker = Worker.get_worker()

    await worker.enqueue(json)
    return {"enqueued": True}


@app.on_event("startup")
async def startup_event():
    """Prepare the worker.

    Creates a new worker object and launches it as a future task.
    """
    loop = asyncio.get_running_loop()
    worker = Worker.get_worker()
    worker.task = asyncio.ensure_future(worker.run(), loop=loop)

    deployment_status_worker = DeploymentStatusWorker.get_worker()
    deployment_status_worker.task = asyncio.ensure_future(deployment_status_worker.run(), loop=loop)


def get_digest(data: bytes) -> str:
    """Calculate the digest of a webhook body.

    Uses the environment variable `GITHUB_WEBHOOK_KEY` as the secret hash key.
    """
    return hmac.new(settings.GITHUB_WEBHOOK_KEY.encode(), data, hashlib.sha1).hexdigest()


def validate_signature(signature: str, digest: str):
    parts = signature.split("=")
    if not len(parts) == 2 or parts[0] != "sha1" or not hmac.compare_digest(parts[1], digest):
        raise HTTPException(400, "Invalid digest, aborting")
