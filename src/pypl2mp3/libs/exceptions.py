#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module defines a custom exception class for the application.

This is the base class used to create module-specific exceptions
and handle errors consistently throughout the application.

It also facilitates the global sharing of new features or changes 
to the exception handling process.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""


class AppBaseException(Exception):
    """
    Custom exception class for the application.
    """

    def __init__(self, message: str):
        """
        Initializes an AppBaseException instance with a message.

        Args:
            message: The error message to be displayed.
        """

        self.message = message
        super().__init__(self.__str__())


    def __str__(self) -> str:
        """
        Returns a string representation of the error.

        [Deprecated] If a cause is available (e.g., raise ... from ...), 
        its string representation is appended to the original
        error message.
        """

        # if self.__cause__:
        #     return (
        #         f"{self.message} --> {type(self.__cause__).__name__}: "
        #         f"{self.__cause__.__str__()}"
        #     )
        
        return self.message