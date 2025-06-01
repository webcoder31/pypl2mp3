#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module provides the foundation for consistent error handling across
the application:

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

from typing import Optional


class AppBaseException(Exception):
    """
    Base exception class for all PYPL2MP3 application errors.

    This class serves as the root of the exception hierarchy for the
    application, providing a consistent interface for error handling.

    Inheritance Pattern:
    ```
    Exception
        └── AppBaseException
            ├── RepositoryException
            ├── ImportPlaylistException
            └── ... (other module-specific exceptions)
    ```

    Note:
        All application-specific exceptions should inherit from this class
        to ensure consistent error handling and reporting throughout the
        application.
    """


    def __init__(self, message: str):
        """
        Initialize exception with message.

        Args:
            message (str): Main error message to display
        """
        self.message = message
        super().__init__(self.__str__())


    def __str__(self) -> str:
        """
        Format error message.

        Returns:
            str: Formatted error message
        """
        
        return self.message