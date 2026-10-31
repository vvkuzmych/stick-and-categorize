import logging
import os
import time
from typing import Self


class DropHealthChecks(logging.Filter):
    """The app polls /health every few seconds: keep those lines out of the access log."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


def setup_logging() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("uvicorn.access").addFilter(DropHealthChecks())


class Timer:
    def __enter__(self) -> Self:
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc) -> None:
        self.seconds = time.perf_counter() - self.start
