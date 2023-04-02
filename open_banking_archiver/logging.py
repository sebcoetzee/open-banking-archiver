import logging
import sys
from logging import Formatter, Handler

from colorama import Fore, Style


class StreamHandler(Handler):
    """
    StreamHandler that implements custom logic to conditionally write to stdout
    or stderr depending on the log level.
    """

    def flush(self):
        """
        Flushes the stream.
        """
        self.acquire()
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            self.release()

    def emit(self, record):
        """
        Emit a record to the stdout stream if it's log level is less than ERROR
        and emit a record to stderr if the log level is greater then or equal to
        ERROR.
        """
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                sys.stderr.write(msg + "\n")
            else:
                sys.stdout.write(msg + "\n")
            self.flush()
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            self.handleError(record)


class CLIFormatter(Formatter):
    """
    Custom formatter that prints the message in different colours depending on
    the log level. This is useful for CLI output where timestamps and log levels
    are not necessary to be printed.
    """

    def __init__(self) -> None:
        super().__init__(fmt="%(message)s")

    def format(self, record) -> str:
        formatted_message = super().format(record)
        if record.levelno >= logging.ERROR:
            formatted_message = Fore.RED + formatted_message
        elif logging.INFO > record.levelno:
            formatted_message = Style.DIM + formatted_message

        return formatted_message + Style.RESET_ALL
