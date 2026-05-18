from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from super_dl.core.paths import is_frozen, log_dir

LOG_FILENAME = "super-dl.log"
LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return

    file_handler = RotatingFileHandler(
        log_dir() / LOG_FILENAME,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(file_handler)

    if not is_frozen():
        stderr = logging.StreamHandler()
        stderr.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(stderr)
