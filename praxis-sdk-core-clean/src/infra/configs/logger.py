import logging
import sys

import structlog
from structlog import get_logger


def configure_logging(level=None):
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if level is None else level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


__all__ = (
    "configure_logging",
    "get_logger",
)
