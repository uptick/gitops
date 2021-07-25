import logging


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.args[2] != "/"


logging_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(format=logging_format, level=logging.DEBUG)

# Filter out / from access logs (We don't care about these calls)
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
