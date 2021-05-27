import logging


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/") == -1


# Filter out / from access logs (We don't care about these calls)
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
