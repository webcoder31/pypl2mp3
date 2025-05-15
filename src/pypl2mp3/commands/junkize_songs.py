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

# Third party packages
from colorama import Fore, Style, init

# pypl2mp3 libs
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import (
    CountFormatter, 
    LabelFormatter, 
    check_and_display_song_selection_result,
    format_song_display,
    format_song_details_display,
    prompt_user
)

# Automatically clear style on each print
init(autoreset=True)


def junkize_songs(args: any) -> None:
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

    prompt = args.prompt
    
    # Get list of songs matching criteria
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

    if not prompt and not _confirm_bulk_operation():
        return

    _process_songs(song_files, prompt, args.verbose)


def _process_songs(song_files: list[Path], prompt: bool, verbose: bool) -> None:
    """
    Process each song file for make it "junk".

    Args:
        song_files: List of paths to song files
        prompt: Whether to prompt for confirmation for each song
    """

    count_formatter = CountFormatter(len(song_files))

    for index, song_file in enumerate(song_files, 1):
        counter = count_formatter.format(index)
        song = SongModel(song_file)
        
        print(
            f"\n{format_song_display(song, counter)}  "
            f"{Fore.WHITE + Style.DIM}[https://youtu.be/{song.youtube_id}]"
        )

        if verbose:
            print(format_song_details_display(song, count_formatter))

        if prompt and not _confirm_single_song():
            continue

        _junkize_single_song(song)


def _confirm_bulk_operation() -> bool:
    """
    Request user confirmation for bulk operation.

    Returns:
        bool: True if user confirms, False otherwise
    """

    confirmation = prompt_user(
        "About to clear metadata for all songs and make them \"junk\"" \
            + "Do you want to proceed",
        ["yes", "no"]
    )

    return confirmation == "yes"


def _confirm_single_song() -> bool:
    """
    Request user confirmation for making "junk" a single song.

    Returns:
        bool: True if user confirms, False otherwise
    """

    confirmation = prompt_user(
        "Do you want to clear metadata for this song and make it \"junk\"",
        ["yes", "no"]
    )

    return confirmation.lower() == "yes"


def _junkize_single_song(song: SongModel) -> None:
    """
    Remove tags from a single song and rename it.

    Args:
        song: SongModel instance to be made junk
    """

    song.reset_state()
    song.fix_filename()
    
    print(
        f"Song made \"junk\" and renamed to: {Fore.LIGHTCYAN_EX}{song.filename}"
    )