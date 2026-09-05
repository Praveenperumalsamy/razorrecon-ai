"""
Structured logging configuration.

Production emits single-line JSON logs (easy to ship to
CloudWatch/Datadog/ELK); local dev emits readable console output.
Never logs secrets, tokens, or full request bodies.
"""

import logging
import sys

from pythonjsonlogger import jsonlogger

from app.config import settings


class RequestIdFilter(logging.Filter):
    """Injects the current request_id (set by middleware) into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())

    if settings.LOG_FORMAT == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | req=%(request_id)s | %(message)s"
        )
    handler.setFormatter(formatter)

    root.handlers = [handler]

    # Quiet down noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
