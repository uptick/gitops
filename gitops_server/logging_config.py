import logging


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.args[2] != "/"  # type: ignore


logging_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(format=logging_format, level=logging.INFO)

# Filter out / from access logs (We don't care about these calls)
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
