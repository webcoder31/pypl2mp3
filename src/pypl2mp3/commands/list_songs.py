#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module provides functionality to list songs from a repository 
with optional filtering and detailed information display.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
from pathlib import Path

# Third party packages
from colorama import Fore, init

# pypl2mp3 libs
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import (
    CountFormatter, 
    check_and_display_song_selection_result,
    format_song_display,
    format_song_details_display
)

# Automatically clear style on each print
init(autoreset=True)


def list_songs(args: any) -> None:
    """
    List songs from the repository with optional filtering and verbose output.

    Args:
        args: Command line arguments containing:
            - repo: Path to the repository
            - keywords: Search keywords for filtering songs
            - match: Threshold for keyword matching
            - playlist: Playlist identifier for filtering
            - verbose: Flag for detailed output

    Raises:
        FileNotFoundError: If the repository path doesn't exist
    """

    song_files = get_repository_song_files(
        Path(args.repo),
        keywords=args.keywords,
        filter_match_threshold=args.match,
        playlist_identifier=args.playlist,
    )

    # Check if some songs match selection crieria
    # iI none, then return
    try:
        check_and_display_song_selection_result(song_files)
    except SystemExit:
        return
    
    if not args.verbose:
        print()
    
    _display_songs(song_files, args.verbose)


def _display_songs(song_files: list[Path], verbose: bool) -> None:
    """
    Display song information with optional verbose details.

    Args:
        song_files: List of paths to song files
        verbose: Whether to show detailed information
    """

    count_formatter = CountFormatter(len(song_files))
    
    for index, song_file in enumerate(song_files, 1):
        counter = count_formatter.format(index)
        song = SongModel(song_file)
        
        print(("", "\n")[verbose] + format_song_display(song, counter))
        
        if verbose:
            print(format_song_details_display(song, count_formatter))