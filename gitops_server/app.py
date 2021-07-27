import os

import sentry_sdk
from fastapi import FastAPI
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from . import settings

app = FastAPI()

# Sentry Setup
if sentry_dsn := os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=settings.CLUSTER_NAME,
    )
    sentry_sdk.set_tag("cluster_name", settings.CLUSTER_NAME)
    app.add_middleware(SentryAsgiMiddleware)
