#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module handles the removal of ID3 tags from audio files.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
from pathlib import Path
from typing import Any, List

# Third party packages
from colorama import Fore, Style

# pypl2mp3 libs
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import ProgressCounter, format_song_display


def junkize_songs(args: Any) -> None:
    """
    Remove ID3 tags from song files based on provided arguments 
    and rename them marked as "junk".

    Args:
        args: Command line arguments with the following attributes:
            - repo (str): Path to the repository containing songs
            - prompt (bool): Whether to prompt for confirmation for each song
            - keywords (List[str]): Keywords to filter songs
            - match (float): Threshold for keyword matching
            - playlist (str): Playlist identifier for filtering

    Raises:
        FileNotFoundError: If the repository path doesn't exist
    """

    should_prompt_per_song = args.prompt
    
    # Get list of songs matching criteria
    song_files = get_repository_song_files(
        Path(args.repo),
        keywords=args.keywords,
        filter_match_threshold=args.match,
        playlist_identifier=args.playlist,
        display_summary=True
    )

    if not song_files:
        print(f"{Fore.YELLOW}No matching songs found.{Style.RESET_ALL}")
        return

    if not _confirm_bulk_operation(should_prompt_per_song):
        return

    _process_songs(song_files, should_prompt_per_song)


def _process_songs(song_files: List[Path], should_prompt_per_song: bool) -> None:
    """
    Process each song file for make it "junk".

    Args:
        song_files: List of paths to song files
        should_prompt_per_song: Whether to prompt for confirmation for each song
    """

    progress_counter = ProgressCounter(len(song_files))

    for index, song_file in enumerate(song_files, 1):
        counter = progress_counter.format(index)
        song = SongModel(song_file)
        
        print(f"\n{format_song_display(counter, song)}  "
            + f"{Fore.WHITE + Style.DIM}[https://youtu.be/{song.youtube_id}]")

        if should_prompt_per_song and not _confirm_single_song():
            continue

        _junkize_single_song(song)


def _confirm_bulk_operation(should_prompt_per_song: bool) -> bool:
    """
    Request user confirmation for bulk operation.

    Args:
        should_prompt_per_song: Whether individual prompts will be shown

    Returns:
        bool: True if user confirms, False otherwise
    """

    if should_prompt_per_song:
        return True

    confirmation = input(
        f"\n{Style.BRIGHT}{Fore.LIGHTBLUE_EX}This will make \"junk\" all songs found. Continue "
        + f"{Style.RESET_ALL}({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? "
    )

    return confirmation.lower() == "yes"


def _confirm_single_song() -> bool:
    """
    Request user confirmation for making "junk" a single song.

    Returns:
        bool: True if user confirms, False otherwise
    """

    confirmation = input(
        f"{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to clear metadata for this song and make it \"junk\""
        + f"{Style.RESET_ALL} ({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? "
    )

    return confirmation.lower() == "yes"


def _junkize_single_song(song: SongModel) -> None:
    """
    Remove tags from a single song and rename it.

    Args:
        song: SongModel instance to be untagged
    """

    song.reset_state()
    song.fix_filename()
    
    print(f"Song untagged and renamed to: {Fore.LIGHTCYAN_EX}{song.filename}{Fore.RESET}")