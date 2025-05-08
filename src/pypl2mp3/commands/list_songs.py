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
from typing import Any

# Third party packages
from colorama import Fore

# pypl2mp3 libs
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import LabelFormatter, ProgressCounter, format_song_display


def list_songs(args: Any) -> None:
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
        display_summary=True
    )

    if not song_files:
        print(f"{Fore.YELLOW}No matching songs found.{Fore.RESET}")
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

    progress_counter = ProgressCounter(len(song_files))
    
    for index, song_file in enumerate(song_files, 1):
        counter = progress_counter.format(index)
        song = SongModel(song_file)
        
        print(("", "\n")[verbose] + format_song_display(counter, song))
        
        if verbose:
            _display_verbose_info(song, progress_counter)


def _display_verbose_info(song: SongModel, progress_counter: ProgressCounter) -> None:
    """
    Display detailed information about a song.

    Args:
        song: Song model containing song metadata
        progress_counter: Counter for formatting output
    """
    
    label_formatter = LabelFormatter(9)
    placeholder = progress_counter.placeholder()
    
    verbose_fields = {
        "Playlist": song.playlist,
        "Filename": song.filename,
        "Link": f"https://youtu.be/{song.youtube_id}"
    }
    
    for label, value in verbose_fields.items():
        print(f"{placeholder}  "
            + f"{label_formatter.format(label)}"
            + f"{Fore.LIGHTBLUE_EX}{value}{Fore.RESET}")