"""Project logging.

Uses loguru when available (nicer formatting, listed in requirements). Falls back
to the stdlib `logging` module so the package still imports and runs in a minimal
environment -- the deterministic core (AQI, PHV, Gi*, DBSCAN) must not hard-depend
on loguru just to be used or tested.
"""

from __future__ import annotations

import sys

_CONFIGURED = False


def _safe_stderr_sink(message):
    """Write loguru messages even when the Windows console uses cp1252."""
    text = str(message)
    try:
        sys.stderr.write(text)
    except UnicodeEncodeError:
        sys.stderr.write(text.encode("ascii", errors="replace").decode("ascii"))
    sys.stderr.flush()


try:

    from loguru import logger as _loguru_logger

    _HAVE_LOGURU = True
except ModuleNotFoundError:  # pragma: no cover - exercised only without loguru
    _HAVE_LOGURU = False


def get_logger(name: str | None = None):
    """Return a logger bound to `name`, configuring the sink once."""
    global _CONFIGURED
    ctx = name or "isro_aqi"

    if _HAVE_LOGURU:
        if not _CONFIGURED:
            _loguru_logger.remove()
            _loguru_logger.add(
                                _safe_stderr_sink,
                level="INFO",

                format=(
                    "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
                    "<cyan>{extra[ctx]}</cyan> - <level>{message}</level>"
                ),
            )
            _CONFIGURED = True
        return _loguru_logger.bind(ctx=ctx)

    # stdlib fallback
    import logging

    if not _CONFIGURED:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
            datefmt="%H:%M:%S",
        )
        _CONFIGURED = True
    return logging.getLogger(ctx)
