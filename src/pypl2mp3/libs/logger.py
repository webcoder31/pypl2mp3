#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module provides a custom logging system with:
- Console output with color-coded log levels
- Optional file logging with detailed formatting
- Support for shortened stack traces
- Configurable verbosity levels
- Exception chain tracking

The logger supports both development (file logging, all levels)
and production (console only, warnings and above) configurations.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
from dataclasses import dataclass
import logging
import sys
import traceback
from typing import Any, Optional, Union, Dict, List

# Third-party packages
from colorama import Fore, Style, init

# ------------------------
# Constants
# ------------------------

# Log levels
DEBUG = logging.DEBUG         # Detailed information for debugging
INFO = logging.INFO           # General information about program execution
WARNING = logging.WARNING     # Warning messages for potential issues
ERROR = logging.ERROR         # Error messages for recoverable problems
CRITICAL = logging.CRITICAL   # Critical errors that may cause program termination

# Default configuration
DEFAULT_CONSOLE_LEVEL = WARNING   # Only show warnings and above in console
DEFAULT_FILE_LEVEL = DEBUG        # Log everything to file if enabled
DEFAULT_VERBOSE_ERRORS = False    # Don't show stack traces by default
DEFAULT_ENABLE_FILE = False       # Console-only logging by default

# Formatting
LOG_FORMAT = "%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
INDENT = " " * 3  # Indentation for multi-line log messages

# ------------------------
# Logger Class
# ------------------------

class Logger:
    """
    A class for logging messages to both console and file.

    This class provides methods to log messages at different 
    levels (debug, info, warning, error, critical) and allows 
    for customization of the logging format and handlers.
    """

    # Map string level names to logging module constants
    LOG_LEVELS: Dict[str, int] = {
        "DEBUG": DEBUG,
        "INFO": INFO,
        "WARNING": WARNING,
        "ERROR": ERROR,
        "CRITICAL": CRITICAL
    }


    def __init__(
        self,
        console_handler_level: Union[str, int] = DEFAULT_CONSOLE_LEVEL,
        verbose_errors_enabled: bool = DEFAULT_VERBOSE_ERRORS,
        enable_file_handler: bool = DEFAULT_ENABLE_FILE,
        file_handler_log_file: Optional[str] = None,
        file_handler_level: Union[str, int] = DEFAULT_FILE_LEVEL,
        file_handler_traceback_enabled: bool = False
    ) -> None:
        """
        Initialize a logger with configurable console and file output.

        Creates a logger that can write to both console and file with different
        configurations for each. Console output is colorized and can be configured
        to show different levels of detail. File output provides more detailed
        logging with timestamps and optional stack traces.

        Args:
            console_handler_level (Union[str, int], optional): Minimum level for
                console output. Can be string ("DEBUG", "INFO", etc) or logging
                constant. Defaults to WARNING (show warnings and above).
            verbose_errors_enabled (bool, optional): Whether to show shortened
                stack traces in console output. Defaults to False.
            enable_file_handler (bool, optional): Whether to enable logging to
                file. Defaults to False.
            file_handler_log_file (Optional[str], optional): Path to log file.
                Required if file_handler_enabled is True. Defaults to None.
            file_handler_level (Union[str, int], optional): Minimum level for
                file output. Defaults to DEBUG (log everything).
            file_handler_traceback_enabled (bool, optional): Whether to include
                full stack traces in file output. Defaults to False.

        Example:
            >>> # Basic console-only logger
            >>> logger = Logger()
            >>> # Full debug logging to file
            >>> logger = Logger(
            ...     enable_file_handler=True,
            ...     file_handler_log_file="debug.log",
            ...     file_handler_level="DEBUG"
            ... )
            >>> # Console logger with stack traces
            >>> logger = Logger(verbose_errors_enabled=True)
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


    def _get_short_tracebacks(self, exc_info: tuple[type, Exception, Any]) -> List[str]:
        """
        Extract simplified traceback information from exception chain.

        Follows exception chain through __cause__ and __context__ to build
        a list of error messages without full stack traces. Useful for
        console output where full tracebacks would be too verbose.

        Args:
            exc_info (tuple[type, Exception, Any]): Exception info from
                sys.exc_info() containing (type, value, traceback)

        Returns:
            List[str]: List of error messages in reverse chronological order
                (most recent first)

        Example:
            ```
            try:
                raise ValueError("Invalid") from FileNotFoundError("Missing")
            except Exception:
                msgs = _get_short_tracebacks(sys.exc_info())
                # ['ValueError: Invalid', 'FileNotFoundError: Missing']
            ```
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
        Create a color-coded formatter for console output.

        Creates a ConsoleHandlerFormatter that:
        - Adds color based on log level (using LEVEL_COLORS)
        - Formats messages with level prefix: [LEVEL] message
        - Optionally adds indented and numbered stack traces
        - Preserves ANSI color through multi-line output

        Returns:
            logging.Formatter: Configured formatter instance that
                produces colored, properly formatted console output

        Example output:
            [INFO] Starting process...             # Green
            [WARNING] File exists, overwriting...  # Yellow
            [ERROR] Process failed:                # Red
               [2] ValueError: Invalid input
               [1] OSError: File not found
        """

        # Define a reference to the parent logger instance
        # to access its attributes and methods within the nested class
        # (e.g., to access the file handler and traceback attributes)
        parent = self

        class ConsoleHandlerFormatter(logging.Formatter):
            """
            Format console log messages with color and optional stack traces.

            Provides:
            - Color-coded output based on log level
            - Consistent indentation and formatting
            - Optional shortened stack traces for errors
            - Exception chain tracking

            The formatter uses ANSI color codes from colorama and applies:
            - Blue for DEBUG
            - Green for INFO
            - Yellow for WARNING
            - Red for ERROR
            - Magenta for CRITICAL

            Stack traces (when enabled) are shown in the same color as
            the log level, indented, and numbered to show the chain
            of exceptions.

            Example output:
                [ERROR] Failed to process file
                   [2] ValueError: Invalid format
                   [1] FileNotFoundError: File does not exist
            """

            # Define color codes for different log levels
            LOG_COLORS = {
                logging.DEBUG: Fore.BLUE,
                logging.INFO: Fore.GREEN,
                logging.WARNING: Fore.YELLOW,
                logging.ERROR: Fore.RED,
                logging.CRITICAL: Fore.MAGENTA
            }
            

            def format(self, record: logging.LogRecord) -> str:
                """
                Format a log record with color coding and optional stack traces.

                Applies consistent formatting to log records:
                1. Colors the output based on log level
                2. Adds [LEVEL] prefix in the correct color
                3. Formats the message text
                4. Optionally adds indented stack traces for errors
                5. Ensures ANSI color codes are properly reset

                Args:
                    record (logging.LogRecord): Log record to format containing:
                        - levelno: Numeric logging level
                        - levelname: Level name (DEBUG, INFO, etc)
                        - msg: The log message
                        - exc_info: Exception info if any

                Returns:
                    str: Fully formatted log entry with colors and layout

                Example:
                    Input record with level=ERROR, msg="Failed", exc_info=True
                    Output (with colors):
                        [ERROR] Failed
                           [2] ValueError: Invalid input
                           [1] IOError: File not found
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
        return ConsoleHandlerFormatter("%(message)s")


    def _add_console_handler(self) -> None:
        """
        Set up console output handler with color formatting.

        Creates and configures a StreamHandler that:
        - Writes to stdout using sys.stdout
        - Uses color-coded formatting (ConsoleHandlerFormatter)
        - Respects minimum log level from console_handler_level
        - Prevents duplicate handlers
        
        The handler is only added if no console handler exists yet.
        This ensures we don't get duplicate console output.

        Example:
            >>> logger = Logger(console_handler_level="INFO")
            >>> logger.info("Visible")      # Shows in console
            >>> logger.debug("Hidden")      # Not shown (below INFO)
        """

        if not self.console_handler:
            self.console_handler = logging.StreamHandler(sys.stdout)
            self.console_handler.setLevel(self.console_handler_level)
            self.console_handler.setFormatter(self._console_handler_formatter())
            self.logger.addHandler(self.console_handler)


    def enable_console_handler(self) -> None:
        """
        Enable logging to console with color-coded output.

        Adds or re-enables console output using settings from initialization:
        - Uses configured minimum log level
        - Applies color coding based on log level
        - Shows stack traces if verbose_errors_enabled is True

        If console output is already enabled, this method has no effect.
        Use disable_console_handler() to turn off console output.

        Example:
            >>> logger.disable_console_handler()  # Turn off console
            >>> logger.warning("Hidden")          # Not shown
            >>> logger.enable_console_handler()   # Turn back on
            >>> logger.warning("Visible")         # Shows in yellow
            [WARNING] Visible
        """

        self._add_console_handler()


    def disable_console_handler(self) -> None:
        """
        Disable all console output.

        Removes the console handler if one exists, stopping all output
        to stdout. File logging (if enabled) continues to work normally.

        The handler is properly cleaned up to prevent resource leaks.
        Use enable_console_handler() to restore console output.

        Example:
            >>> logger.warning("Visible")         # Shows in console
            [WARNING] Visible
            >>> logger.disable_console_handler()  # Turn off console
            >>> logger.error("Hidden")            # Only goes to file
            >>> # Nothing shown in console
        """

        if self.console_handler:
            self.logger.removeHandler(self.console_handler)
            self.console_handler = None


    def _file_handler_formatter(self) -> logging.Formatter:
        """
        Create a detailed formatter for file output.

        Creates a FileHandlerFormatter that formats messages with:
        - Millisecond-precision timestamps
        - Log level indicators
        - Full message text
        - Optional stack traces based on settings
        - Clean separation between entries
        - Exception chain preservation

        The format follows: "YYYY-MM-DD HH:MM:SS.mmm | LEVEL | message"
        
        Returns:
            logging.Formatter: Configured formatter that produces
                consistently formatted log file entries

        Example output:
            2024-01-01 12:34:56.789 | INFO | Process started
            2024-01-01 12:34:57.123 | ERROR | Operation failed
            Traceback (most recent call last):
              File "app.py", line 10...
        """

        # Define a reference to the parent logger instance
        # to access its attributes and methods within the nested class
        # (e.g., to access the traceback flag)
        parent = self

        class FileHandlerFormatter(logging.Formatter):
            """
            Format file log messages with timestamps and stack traces.

            Provides:
            - Timestamp with millisecond precision
            - Consistent message formatting
            - Log level indication
            - Full stack traces for CRITICAL
            - Optional stack traces for other levels
            - Exception chain preservation

            Format: "YYYY-MM-DD HH:MM:SS.mmm | LEVEL | message"

            Stack traces are included based on:
            - CRITICAL: Always included
            - ERROR: Included if traceback_enabled
            - Others: Never included

            Example output:
                2024-01-01 12:34:56.789 | ERROR | Failed to process file
                Traceback (most recent call last):
                  File "app.py", line 10, in process_file
                    ...
            """


            def format(self, record: logging.LogRecord) -> str:
                """
                Format a log record with timestamp and optional stack traces.

                Creates a detailed log entry with:
                1. Millisecond-precision timestamp
                2. Log level indicator
                3. Full message text
                4. Optional stack traces based on settings and level:
                   - CRITICAL: Always includes full trace
                   - ERROR: Includes if traceback_enabled=True
                   - Others: Never includes traces

                Args:
                    record (logging.LogRecord): Log record to format containing:
                        - levelno: Numeric logging level
                        - msg: The log message
                        - exc_info: Exception info tuple or None
                        - msecs: Milliseconds part of timestamp
                        - asctime: Formatted timestamp base

                Returns:
                    str: Fully formatted log entry with proper layout and
                        line breaks for readability

                Example:
                    Input record: ERROR level with exception
                    Output:
                        2024-01-01 12:34:56.789 | ERROR | Operation failed

                        Traceback (most recent call last):
                          File "app.py", line 10...
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
        Set up file output handler with detailed formatting.

        Creates and configures a FileHandler that:
        - Writes to the specified log file path
        - Uses detailed timestamps and formatting
        - Includes stack traces based on settings
        - Prevents duplicate handlers
        - Handles file creation/opening

        The handler is only added if:
        - No file handler exists yet
        - A valid log file path is configured

        Example:
            >>> logger = Logger(
            ...     enable_file_handler=True,
            ...     file_handler_log_file="app.log"
            ... )
            >>> logger.info("Saved to file")  # Written to app.log
        """

        if not self.file_handler and self.file_handler_log_file:
            self.file_handler = logging.FileHandler(self.file_handler_log_file)
            self.file_handler.setLevel(self.file_handler_level)
            self.file_handler.setFormatter(self._file_handler_formatter())
            self.logger.addHandler(self.file_handler)


    def enable_file_handler(
        self,
        log_file: Optional[str] = None,
        level: Optional[str] = None,
        enable_traceback: Optional[bool] = None
    ) -> None:
        """
        Enable or reconfigure logging to file.

        Sets up file logging with detailed formatting and timestamps.
        If file logging is already active, reconfigures it with
        any new settings provided.

        Args:
            log_file (Optional[str], optional): Path to log file. If None,
                keeps current path. Defaults to None.
            level (Optional[str], optional): Minimum level to log
                ("DEBUG" through "CRITICAL"). If None, keeps current.
                Defaults to None.
            enable_traceback (Optional[bool], optional): Whether to include
                stack traces. If None, keeps current. Defaults to None.

        Any parameter left as None keeps its current value. To modify
        specific settings without changing others, provide only the
        parameters you want to change.

        Example:
            >>> # Basic file logging
            >>> logger.enable_file_handler("app.log")
            >>> # Change just the log level
            >>> logger.enable_file_handler(level="DEBUG")
            >>> # Full reconfiguration
            >>> logger.enable_file_handler(
            ...     "debug.log",
            ...     "DEBUG",
            ...     enable_traceback=True
            ... )
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
        Disable logging to file.

        Properly closes and removes the file handler if one exists.
        After calling this:
        - No new messages will be written to the log file
        - The file handle is properly closed to prevent resource leaks
        - Console logging (if enabled) continues normally
        
        The log file itself remains on disk and can still be read.
        Use enable_file_handler() to start logging to file again.

        Example:
            >>> logger.enable_file_handler("app.log")
            >>> logger.info("Saved")          # Written to file
            >>> logger.disable_file_handler() # Stop file logging
            >>> logger.info("Console only")   # Only to console
        """

        if self.file_handler:
            self.logger.removeHandler(self.file_handler)
            self.file_handler.close()
            self.file_handler = None


    def enable_verbose_errors(self) -> None:
        """
        Enable display of shortened stack traces in console output.

        When enabled, ERROR and CRITICAL messages in console output will
        include a simplified chain of exceptions showing:
        - Exception types
        - Error messages
        - Exception chain (cause/context)
        
        This provides more debug information while keeping output readable.
        File logging is not affected by this setting.

        Example:
            >>> logger.enable_verbose_errors()
            >>> try:
            ...     1/0
            ... except Exception as e:
            ...     logger.error(e)
            [ERROR] division by zero
               [1] ZeroDivisionError: division by zero
        """
        self.verbose_errors_enabled = True


    def disable_verbose_errors(self) -> None:
        """
        Disable stack traces in console output.

        When disabled, ERROR and CRITICAL messages in console output will
        only show the error message without any stack trace information.
        This produces cleaner, more user-friendly output.
        
        File logging is not affected by this setting.

        Example:
            >>> logger.disable_verbose_errors()
            >>> try:
            ...     1/0
            ... except Exception as e:
            ...     logger.error(e)
            [ERROR] division by zero
        """
        self.verbose_errors_enabled = False


    def debug(self, msg: Any) -> None:
        """
        Log detailed information for debugging purposes.

        Messages at this level provide detailed technical information
        useful for debugging but normally not shown to users.

        Args:
            msg (Any): Message to log. Will be converted to string via str()

        Example:
            >>> logger.debug("Processing item 123 with params {x: 42}")
            [DEBUG] Processing item 123 with params {x: 42}
        """
        self.logger.debug(str(msg))


    def info(self, msg: Any) -> None:
        """
        Log general information about program operation.

        Messages at this level provide confirmation that things
        are working as expected.

        Args:
            msg (Any): Message to log. Will be converted to string via str()

        Example:
            >>> logger.info("Successfully processed 10 items")
            [INFO] Successfully processed 10 items
        """
        self.logger.info(str(msg))


    def warning(self, msg: Any) -> None:
        """
        Log warnings about potential problems.

        Messages at this level indicate that something unexpected
        happened, but the program can continue operating.

        Args:
            msg (Any): Message to log. Will be converted to string via str()

        Example:
            >>> logger.warning("File is larger than expected")
            [WARNING] File is larger than expected
        """
        self.logger.warning(str(msg))


    def error(self, error: Union[Exception, str], msg: Optional[str] = None) -> None:
        """
        Log errors that prevent normal operation.

        Messages at this level indicate that the program encountered
        an error but can recover or gracefully degrade functionality.

        Args:
            error (Union[Exception, str]): Error to log. Can be exception or message
            msg (Optional[str], optional): Override message if error is exception.
                Defaults to None (use error's message).

        Example:
            >>> try:
            ...     raise ValueError("Bad input")
            ... except ValueError as e:
            ...     logger.error(e)
            [ERROR] Bad input
            >>> logger.error(e, "Failed to process input")
            [ERROR] Failed to process input
        """
        self.logger.error(msg or str(error), exc_info=bool(msg))


    def critical(self, error: Union[Exception, str], msg: Optional[str] = None) -> None:
        """
        Log severe errors that prevent program operation.

        Messages at this level indicate that the program cannot continue
        running normally and will likely terminate or severely degrade.
        Always includes full stack traces in file output.

        Args:
            error (Union[Exception, str]): Error to log. Can be exception or message
            msg (Optional[str], optional): Override message if error is exception.
                Defaults to None (use error's message).

        Example:
            >>> try:
            ...     raise RuntimeError("Fatal error")
            ... except RuntimeError as e:
            ...     logger.critical(e)
            [CRITICAL] Fatal error
            Traceback (most recent call last):
              ...
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