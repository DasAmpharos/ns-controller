import logging
import sys
from enum import StrEnum


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

def setup_logging(log_level: LogLevel):
    # Remove all handlers associated with the root logger object
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Set up handler for ERROR and above to stderr
    err_handler = logging.StreamHandler(sys.stderr)
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    # Set up handler for lower levels to default stream (stdout)
    out_handler = logging.StreamHandler(sys.stdout)
    out_handler.setLevel(getattr(logging, log_level))
    out_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    out_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    logging.basicConfig(level=getattr(logging, log_level), handlers=[out_handler, err_handler])