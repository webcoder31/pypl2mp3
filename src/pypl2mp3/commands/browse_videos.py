#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module handles opening song videos on YouTube.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
from pathlib import Path
import webbrowser

# Third party packages
from colorama import Fore, Style, init

# pypl2mp3 libs
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import (
    LabelFormatter, 
    CountFormatter, 
    check_and_display_song_selection_result,
    format_song_display,
    format_song_details_display,
    prompt_user
)

# Automatically clear style on each print
init(autoreset=True)


def browse_videos(args: any) -> None:
    """
    Prompt to open song videos on YouTube, based on user selection.

    Args:
        args: Command line arguments with the following attributes:
            - repo: Repository path
            - keywords: Search keywords
            - match: Filter match threshold
            - playlist: Playlist identifier
            - verbose: Verbose output flag
    """

    song_files = get_repository_song_files(
        Path(args.repo),
        keywords=args.keywords,
        filter_match_threshold=args.match,
        playlist_identifier=args.playlist,
    )
    
    # Check if some songs match selection crieria
    # If none, then return
    try:
        check_and_display_song_selection_result(song_files)
    except SystemExit:
        return

    count_formatter = CountFormatter(len(song_files))

    for index, song_file in enumerate(song_files, 1):
        song = SongModel(song_file)
        counter = count_formatter.format(index)
        
        print(f"\n{format_song_display(song, counter)}")
        
        if args.verbose:
            print(format_song_details_display(song, count_formatter))

        response = prompt_user(
            "Do you want to open video for this song",
            ["yes", "no"]
        )
        if response == "yes":
            url = f"https://youtu.be/{song.youtube_id}"
            webbrowser.open(url, new=0, autoraise=True)
