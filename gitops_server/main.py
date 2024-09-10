import asyncio
import hashlib
import hmac
import logging
import logging.config

from fastapi import HTTPException, Request
from uptick_observability.fastapi import manually_instrument_fastapi  # type: ignore[import-untyped]
from uptick_observability.logging import (  # type: ignore[import-untyped]
    DEFAULT_LOGGING_CONFIG_DICT,
    manually_instrument_logging,
)

from gitops_server import settings
from gitops_server.app import app
from gitops_server.workers import DeploymentStatusWorker, DeployQueueWorker

manually_instrument_logging()
manually_instrument_fastapi()

logging.config.dictConfig(DEFAULT_LOGGING_CONFIG_DICT)
logger = logging.getLogger("gitops")


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.args[2] not in {"/readyz", "/livez", "/"}  # type: ignore


# Filter out / from access logs (We don't care about these calls)
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())


@app.get("/")
@app.get("/readyz")
@app.get("/livez")
def health_check():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    """Fulfil a git webhook request"""
    digest = get_digest(await request.body())
    signature = request.headers["X-Hub-Signature"]

    validate_signature(signature, digest)

    json = await request.json()

    worker = DeployQueueWorker.get_worker()

    await worker.enqueue(json)
    return {"enqueued": True}


@app.on_event("startup")
async def startup_event():
    """Prepare the worker.

    Creates a new worker object and launches it as a future task.
    """
    loop = asyncio.get_running_loop()
    deploy_queue_worker = DeployQueueWorker.get_worker()
    deploy_queue_worker.task = asyncio.ensure_future(deploy_queue_worker.run(), loop=loop)

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
