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
from typing import Any, List

# Third party packages
from colorama import Fore

# pypl2mp3 libs
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import LabelFormatter, ProgressCounter, format_song_display


def list_junks(args: Any) -> None:
    """
    List all songs marked as junk in the repository, with optional filtering and detailed information.

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
        display_summary=True
    )

    if not song_files:
        print(f"{Fore.YELLOW}No matching junk songs found.{Fore.RESET}")
        return

    _display_song_information(song_files, args.verbose)


def _display_song_information(song_files: list[str], verbose: bool) -> None:
    """
    Display information about songs, either in brief or verbose format.

    Args:
        song_files: List of paths to song files
        verbose: Whether to show detailed information
    """

    if not verbose:
        print()

    progress_counter = ProgressCounter(len(song_files))
    
    for index, song_file in enumerate(song_files, 1):
        counter = progress_counter.format(index)
        song = SongModel(song_file)
        
        print(("", "\n")[verbose] + format_song_display(counter, song))
        
        if verbose:
            _display_verbose_information(song, progress_counter)


def _display_verbose_information(song: SongModel, progress_counter: ProgressCounter) -> None:
    """
    Display detailed information about a song including playlist, filename, and status.

    Args:
        song: Song model instance
        progress_counter: Progress counter for formatting output
    """

    label_formatter = LabelFormatter(9)
    placeholder = progress_counter.placeholder()

    # Display basic information
    print(f"{placeholder}  {label_formatter.format('Playlist')}"
        + f"{Fore.LIGHTBLUE_EX}{song.playlist}{Fore.RESET}")
    print(f"{placeholder}  {label_formatter.format('Filename')}"
        + f"{Fore.LIGHTBLUE_EX}{song.filename}{Fore.RESET}")
    print(f"{placeholder}  {label_formatter.format('Link')}"
        + f"{Fore.LIGHTBLUE_EX}https://youtu.be/{song.youtube_id}{Fore.RESET}")

    # Display status information
    status_message = _get_song_status_message(song)
    print(f"{placeholder}  {label_formatter.format('Status')}{status_message}")


def _get_song_status_message(song: SongModel) -> str:
    """
    Generate appropriate status message for a song based on its state.

    Args:
        song: Song model instance

    Returns:
        str: Formatted status message with color coding
    """

    if song.should_be_tagged or not song.has_cover_art:
        return (f"{Fore.MAGENTA}Song is not tagged or is missing cover art "
              + f"and should be youtubed first before being fixed.{Fore.RESET}")
    if song.should_be_shazamed:
        return (f"{Fore.MAGENTA}Song is tagged and has cover art but it "
              + f"should be shazamed to get trusted ones.{Fore.RESET}")
    if song.should_be_renamed:
        return (f"{Fore.MAGENTA}Song is shazamed and tagged but it "
              + f"should be renamed.{Fore.RESET}")
    return (f"{Fore.LIGHTYELLOW_EX}Song is shazamed, tagged and named accordingly. "
          + f"Unjunk it using \"--prompt\" option{Fore.RESET}")
