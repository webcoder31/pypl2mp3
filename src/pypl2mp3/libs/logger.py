#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module provides a custom logger class for logging messages to  
both console and file. It includes methods for logging at different
levels (debug, info, warning, error, critical) and allows for 
customization of the logging format and handlers.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
import logging
import sys
import traceback

# Third-party packages
from colorama import Fore, Style, init

# Automatically clear style on each print
init(autoreset=True)


class Logger:
    """
    A class for logging messages to both console and file.
    This class provides methods to log messages at different 
    levels (debug, info, warning, error, critical) and allows 
    for customization of the logging format and handlers.
    """

    LOG_LEVELS: map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    """
    A dictionary mapping string log levels to their corresponding
    logging module constants.
    """

    def __init__(self, 
        console_handler_level=logging.INFO, 
        verbose_errors_enabled=False, 
        enable_file_handler=False, 
        file_handler_log_file=None, 
        file_handler_level=logging.DEBUG,
        file_handler_traceback_enabled = False
    ) -> "Logger":
        """
        Initializes the Logger instance with a specified log file, 
        console logging level, and file logging option.

        Args:
            console_handler_level: The logging level for console output 
                ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
            verbose_errors_enabled: Whether to include
                verbose error messages for console and file logging.
            file_handler_log_file: The path of the log file to write logs to.
            file_handler_enabled: Whether to enable file logging.
            file_handler_traceback_enabled: Whether to include
                traceback information in the messages logged in log file.
        """

        # Set up the logger
        self.logger: logging.Logger = logging.getLogger("AppLogger")
        self.logger.setLevel(logging.DEBUG)  # Capture all messages

        self.verbose_errors_enabled: bool = verbose_errors_enabled

        self.console_handler: logging.StreamHandler | None = None
        self.console_handler_level: int = \
            self.LOG_LEVELS.get(console_handler_level, logging.INFO)

        self.file_handler: logging.FileHandler | None = None
        self.file_handler_log_file: str | None = file_handler_log_file
        self.file_handler_level: int = \
            self.LOG_LEVELS.get(file_handler_level, logging.DEBUG)
        self.file_handler_traceback_enabled: bool = \
            file_handler_traceback_enabled

        # Set up the console handler
        self._add_console_handler()

        # Set up the file handler if enabled
        # and a log file is provided
        if enable_file_handler and file_handler_log_file:
            self._add_file_handler()


    def _get_short_tracebacks(self, exc_info: any) -> list[str]:
        """
        Return the chain of exceptions into a list of strings,
        each with type and error message.

        Args:
            exc_info: The exception information (sys.exc_info()).

        Returns:
            A list of strings representing the exception chain.
        """

        tracebacks = []
        tbe = traceback.TracebackException(*exc_info)

        # Follow __cause__ and __context__ to get the full chain
        # of exceptions and store them shortened in the tracebacks list
        # (e.g., type + error message)
        while tbe:
            tracebacks.append(
                "".join(tbe.format_exception_only()).replace("\n", "")
            )
            tbe = tbe.__cause__ or tbe.__context__

        # Return the tracebacks list
        return tracebacks


    def _console_handler_formatter(self) -> logging.Formatter:
        """
        Returns a custom formatter for the console handler.

        This formatter formats log messages with colors based on the log level.
        It also handles exceptions and formats them with a specific
        format to restitute the error chain.
        """

        # Define a reference to the parent logger instance
        # to access its attributes and methods within the nested class
        # (e.g., to access the file handler and traceback attributes)
        parent = self

        class CoonsoleHandlerFormatter(logging.Formatter):
            """
            Custom formatter for console handler to format log messages
            with colors based on log level.

            This formatter also handles exceptions and can provide a
            shortened version of the stack trace along with the message 
            for verbose errors.
            """

            # Define color codes for different log levels
            LOG_COLORS = {
                logging.DEBUG: Fore.BLUE,
                logging.INFO: Fore.GREEN,
                logging.WARNING: Fore.YELLOW,
                logging.ERROR: Fore.RED,
                logging.CRITICAL: Fore.MAGENTA
            }
            

            def format(self, record) -> str:
                """
                Formats the log record into a string with color and style.

                This method is called when a log record is emitted.
                It handles the formatting of the log entry, including
                the log level, message, and any exception information.

                Args:
                    record: The log record to be formatted.

                Returns:
                    A formatted string representing the log message.
                """

                # Set the color based on the log level
                color = self.LOG_COLORS.get(record.levelno, '')

                # Format log entry with color
                log_entry = f"{color}{Style.BRIGHT}[{record.levelname}] " \
                    + f"{record.getMessage()}{Style.RESET_ALL}"

                # Add a shortened version of the exception chain if available 
                # (e.g., in case of error or critical log)
                if record.exc_info and parent.verbose_errors_enabled:
                    tracebacks = parent._get_short_tracebacks(record.exc_info)
                    tracebacks_len = len(tracebacks)
                    for i, msg in enumerate(tracebacks, 0):
                        log_entry += \
                            f"\n{color}{' ' * (len(record.levelname) + 3)}" \
                            + f"{Style.BRIGHT}[{tracebacks_len - i}]" \
                            + f"{Style.NORMAL} {msg}{Style.RESET_ALL}"

                # Return the formatted log entry
                return log_entry

        # Return the custom formatter for console handler
        return CoonsoleHandlerFormatter("%(message)s")


    def _add_console_handler(self) -> None:
        """
        Adds a console handler to the logger if it doesn't already exist.
        This handler writes colored log messages to the console (stdout)
        based on the log level.
        """

        if not self.console_handler:
            self.console_handler = logging.StreamHandler(sys.stdout)
            self.console_handler.setLevel(self.console_handler_level)
            self.console_handler.setFormatter(self._console_handler_formatter())
            self.logger.addHandler(self.console_handler)


    def enable_console_handler(self) -> None:
        """
        Enables console logging by adding a console handler to the logger.
        If the console handler already exists, it does nothing.
        """

        self._add_console_handler()


    def disable_console_handler(self) -> None:
        """
        Disables console logging by removing the console handler 
        from the logger.
        If the console handler doesn't exist, it does nothing.
        """

        if self.console_handler:
            self.logger.removeHandler(self.console_handler)
            self.console_handler = None


    def _file_handler_formatter(self) -> logging.Formatter:
        """
        Returns a custom formatter for the file handler.

        This formatter formats log messages with a specific 
        format including timestamp, level, and message.

        It also handles exceptions and formats them with a specific
        format to restitute the error chain.
        """

        # Define a reference to the parent logger instance
        # to access its attributes and methods within the nested class
        # (e.g., to access the traceback flag)
        parent = self

        class FileHandlerFormatter(logging.Formatter):
            """
            Custom formatter for file handler to format log messages
            with a specific format including timestamp, level, and message.

            This formatter also handles exceptions and can provide a
            shortened version of the stack trace along with the message 
            for verbose errors.
            """

            def format(self, record: logging.LogRecord) -> str:
                """
                Formats the log record into a string.
                This method is called when a log message is emitted.
                It handles the formatting of the log message, including
                the log level, message, and exception information when 
                provided.

                Args:
                    record: The log record to be formatted.

                Returns:
                    A formatted string representing the log message.
                """

                # Manage verbose error logging
                if record.exc_info and parent.verbose_errors_enabled:
                    tracebacks = parent._get_short_tracebacks(record.exc_info)
                    tracebacks_len = len(tracebacks)
                    message = record.getMessage()
                    for i, msg in enumerate(tracebacks, 0):
                        message += f"\n\t[{tracebacks_len - i}] {msg}"

                    # Replace the record message with the one containing the 
                    # original message and the shortened exception chain
                    record.msg = message   

                # If traceback is not enabled and record is not
                # a critical log, set the exception information to None
                # to prevent it from being logged along with the log entry
                if not parent.file_handler_traceback_enabled \
                    and record.levelno != logging.CRITICAL:

                    record.exc_info = None  # 

                # If traceback is enabled, add newline to the record massage
                # to separate the log entry from the exception information
                if record.exc_info and record.levelno >= logging.ERROR:

                    record.msg = f"{record.msg}\n\n"

                # Format record according to the format 
                # specified in the handler constructor
                log_entry = super().format(record)

                # If exception info is available and the log level is ERROR 
                # or CRITICAL, surround the log entry with newlines to separate
                # it from other logs and make it more readable
                if record.exc_info and record.levelno >= logging.ERROR:

                    log_entry = f"\n{log_entry}\n"

                # Return the formatted log record
                return log_entry
        
        # Return the custom formatter for file handler
        # configured with the specified output format and date format
        return FileHandlerFormatter(
            "%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s", 
            "%Y-%m-%d %H:%M:%S"
        )


    def _add_file_handler(self) -> None:
        """
        Adds a file handler to the logger if it doesn't already exist.
        This handler writes log messages to the specified log file.
        """

        if not self.file_handler and self.file_handler_log_file:
            self.file_handler = logging.FileHandler(self.file_handler_log_file)
            self.file_handler.setLevel(self.file_handler_level)
            self.file_handler.setFormatter(self._file_handler_formatter())
            self.logger.addHandler(self.file_handler)


    def enable_file_handler(self, 
        log_file: str | None = None, 
        level: str | None = None, 
        enable_traceback: bool | None = None
    ) -> None:
        """
        Enables file logging by adding a file handler to the logger.
        If the file handler already exists, it does nothing.
        If a new log file is provided, it replaces the existing one.

        Args:
            log_file: The name of the log file to write logs to.
            level: The logging level for file output
                ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
            enable_traceback: A boolean indicating whether to include 
                traceback information in the log messages.
        """

        if self.file_handler:
            # If the file handler already exists, remove it
            self.disable_file_handler()

        if log_file is not None:
            self.file_handler_log_file = log_file

        if level is not None:
            self.file_handler_level = self.LOG_LEVELS.get(level, logging.DEBUG)

        if enable_traceback is not None:
            self.file_handler_traceback_enabled = enable_traceback

        # Add the file handler to the logger
        self._add_file_handler()


    def disable_file_handler(self) -> None:
        """
        Disables file logging by removing the file handler from the logger.
        If the file handler doesn't exist, it does nothing.
        """

        if self.file_handler:
            self.logger.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None


    def enable_verbose_errors(self) -> None:
        """
        Enables verbose error logging.
        This allows for error or critical logs 
        to be logged with a shortened stak trace.
        """

        self.verbose_errors_enabled = True


    def disable_verbose_errors(self) -> None:
        """
        Disables verbose error logging.
        """

        self.verbose_errors_enabled = False


    def debug(self, msg: object) -> None:
        """
        Logs a debug message to the logger.

        Args:
            msg: The message to be logged.
        """

        self.logger.debug(msg)


    def info(self, msg: object) -> None:
        """
        Logs an info message to the logger.

        Args:
            msg: The message to be logged.
        """

        self.logger.info(msg)


    def warning(self, msg: object) -> None:
        """
        Logs a warning message to the logger.

        Args:
            msg: The message to be logged.
        """

        self.logger.warning(msg)


    def error(self, error: object, msg: object | None = None) -> None:
        """
        Logs an error to the logger.

        This method is used for logging errors that occur during
        the execution of the program. It can be used to log exceptions
        or any other error messages.

        If the error is an exception, it logs the exception message
        and the traceback (if enabled) to the log file.

        Args:
            error: The exception to be logged.
            msg: An optional message to be logged in place of the exception one.
        """

        self.logger.error(msg or str(error), exc_info=True)


    def critical(self, error: object, msg: object | None = None) -> None:
        """
        Logs a critical error to the logger.

        This method is used for logging severe errors that may cause 
        the program to terminate.

        If file logging is enabled, it logs the exception message
        and the full traceback (even if not enabled) to the log file.

        Typically, this is used for logging unhandled exceptions
        or for logging critical application errors.

        Args:
            error: The critical error to be logged.
            msg: An optional message to be logged in place of the exception one.
        """

        self.logger.critical(msg or str(error), exc_info=True)


# Create a global logger instance (singleton) to be used throughout all 
# the application modules.
#
# IMPORTANT : Because PYPL2MP3 application uses log messages by design 
# to interact with the user, this instance is configured to only log WARNING, 
# ERROR and CRITICAL level messages to the console.
#
# The file handler is disabled by default and can be enabled via CLI (-d or -D). 
# When enabled, it will log all level messages (DEBUG and above) to a log file.
logger = Logger(console_handler_level="WARNING")