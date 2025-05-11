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
from typing import Any, List

# Third party packages
from colorama import Fore, Style

# pypl2mp3 libs
from pypl2mp3.libs.repository import get_repository_song_files
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import LabelFormatter, CountFormatter, format_song_display


def browse_videos(args: Any) -> None:
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
        display_summary=True
    )
    
    if not song_files:
        print(f"{Fore.YELLOW}No matching songs found.{Fore.RESET}")
        return

    _process_songs(song_files, args.verbose)


def _process_songs(song_files: List[Path], verbose: bool) -> None:
    """
    Process each song, displaying information and handling URL opening.
    
    Args:
        song_files: List of paths to song files
        verbose: Whether to display detailed information
    """

    count_formatter = CountFormatter(len(song_files))
    label_formatter = LabelFormatter(9)

    for index, song_file in enumerate(song_files, 1):
        song = SongModel(song_file)
        counter = count_formatter.format(index)
        
        print(f"\n{format_song_display(counter, song)}")
        
        if verbose:
            _display_verbose_info(count_formatter, label_formatter, song)
            
        if _should_open_url():
            _open_youtube_url(song.youtube_id)


def _display_verbose_info(
        count_formatter: CountFormatter, 
        label_formatter: LabelFormatter, 
        song: SongModel
    ) -> None:

    """
    Display detailed song information in verbose mode.

    Args:
        progress: Progress counter for formatting
        formatter: Label formatter for consistent output
        song: SongModel object containing song details
    """
    placeholder = count_formatter.placeholder()
    print(f"{placeholder}  {label_formatter.format('Playlist')}"
        + f"{Fore.LIGHTBLUE_EX}{song.playlist}{Fore.RESET}")
    
    print(f"{placeholder}  {label_formatter.format('Filename')}"
        + f"{Fore.LIGHTBLUE_EX}{song.filename}{Fore.RESET}")
    
    print(f"{placeholder}  {label_formatter.format('Link')}"
        + f"{Fore.LIGHTBLUE_EX}https://youtu.be/{song.youtube_id}{Fore.RESET}")


def _should_open_url() -> bool:
    """
    Prompt user for URL opening confirmation.

    Returns:
        bool: True if user wants to open URL, False otherwise
    """

    response = input(
        f"{Style.BRIGHT}{Fore.LIGHTBLUE_EX}Do you want to open video for this song "
        + f"{Style.RESET_ALL}({Fore.CYAN}yes{Fore.RESET}/{Fore.CYAN}no{Fore.RESET}) ? "
    )
    return response.lower() == "yes"


def _open_youtube_url(youtube_id: str) -> None:
    """
    Open YouTube URL in default browser.

    Args:
        youtube_id: YouTube video ID
    """
    
    url = f"https://youtu.be/{youtube_id}"
    webbrowser.open(url, new=0, autoraise=True)