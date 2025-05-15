#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module handles the listing of songs marked as junk in the repository.
It provides functionality to display detailed information about songs
that need attention or cleanup.

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
    LabelFormatter, 
    CountFormatter, 
    check_and_display_song_selection_result,
    format_song_display,
    format_song_details_display
)

# Automatically clear style on each print
init(autoreset=True)


def list_junks(args: any) -> None:
    """
    List all songs marked as junk in the repository, 
    with optional filtering and detailed information.

    Args:
        args: Command line arguments containing:
            - repo: Repository path
            - keywords: Filter keywords
            - verbose: Enable detailed output
            - match: Keyword match threshold
            - playlist: Playlist identifier

    Raises:
        FileNotFoundError: If repository path doesn't exist
    """

    song_files = get_repository_song_files(
        Path(args.repo),
        junk_only=True,
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

    _display_songs(song_files, args.verbose)


def _display_songs(song_files: list[str], verbose: bool) -> None:
    """
    Display information about songs, either in brief or verbose format.

    Args:
        song_files: List of paths to song files
        verbose: Whether to show detailed information
    """

    if not verbose:
        print()

    count_formatter = CountFormatter(len(song_files))
    
    for index, song_file in enumerate(song_files, 1):
        counter = count_formatter.format(index)
        song = SongModel(song_file)
        
        print(("", "\n")[verbose] + format_song_display(song, counter))
        
        if verbose:
            print(format_song_details_display(song, count_formatter))
            _print_song_status(song, count_formatter)


def _print_song_status(
        song: SongModel, 
        count_formatter: CountFormatter
    ) -> None:
    """
    Display status of a song

    Args:
        song: Song model instance
        count_formatter: Progress counter for formatting output
    """

    label_formatter = LabelFormatter(9)
    placeholder = count_formatter.placeholder()

    if song.should_be_tagged or not song.has_cover_art:
        status_message = (
            f"{Fore.MAGENTA}Song is not tagged or is missing cover art "
            f"and should be youtubed first before being fixed."
        )
    if song.should_be_shazamed:
        status_message = (
            f"{Fore.MAGENTA}Song is tagged and has cover art but it "
            f"should be shazamed to get trusted ones."
        )
    if song.should_be_renamed:
        status_message = (
            f"{Fore.MAGENTA}Song is shazamed and tagged but it "
            f"should be renamed."
        )
    status_message = (
        f"{Fore.LIGHTGREEN_EX}Song is shazamed, tagged and named accordingly. "
        f"Unjunk it using \"--prompt\" option"
    )

    print(
        f"{placeholder}  {label_formatter.format('Status')}{status_message}"
    )
