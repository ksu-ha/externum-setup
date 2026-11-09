
import logging
import os
from pathlib import Path

from core.security import redact


def get_log_directory():
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))

    directory = base / "externum" / "logs"
    directory.mkdir(parents=True, exist_ok=True)

    return directory


class RedactingFormatter(logging.Formatter):
    def format(self, record):
        record.msg = redact(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: redact(value)
                    for key, value in record.args.items()
                }
            else:
                record.args = tuple(
                    redact(value)
                    for value in record.args
                )

        return super().format(record)


class AppLogger:
    def __init__(self):
        self.directory = get_log_directory()

        self.path = self.directory / "externum.log"

        self.logger = logging.getLogger("externum")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        if not self.logger.handlers:
            handler = logging.FileHandler(
                self.path,
                encoding="utf-8"
            )

            handler.setFormatter(
                RedactingFormatter(
                    "%(asctime)s | %(levelname)s | %(message)s"
                )
            )

            self.logger.addHandler(handler)

    def info(self, message):
        self.logger.info(redact(message))

    def warning(self, message):
        self.logger.warning(redact(message))

    def error(self, message):
        self.logger.error(redact(message))

    def debug(self, message):
        self.logger.debug(redact(message))

    def exception(self, message):
        self.logger.exception(redact(message))

    def get_path(self):
        return str(self.path)

    def get_directory(self):
        return str(self.directory)


def create_logger():
    return AppLogger()
