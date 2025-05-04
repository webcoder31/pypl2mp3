#!/usr/bin/env python3

"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module handles playlist listing functionality.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
from pathlib import Path
import re
from dataclasses import dataclass
from typing import List

# Third party packages
from colorama import Fore, Back, Style

# pypl2mp3 libs
from pypl2mp3.libs.utils import (
    ProgressCounter, 
    get_deterministic_sort_key, 
    extract_youtube_id_from_filename
)


@dataclass
class PlaylistStats:
    """
    Container for playlist statistics.
    """

    total_songs: int
    junk_songs: int

    @property
    def valid_songs(self) -> int:
        """
        Return the number of valid (non-junk) songs.
        """
        
        return self.total_songs - self.junk_songs


def list_playlists(args) -> None:
    """
    List all playlists in the repository with their song statistics.

    Args:
        args: Command line arguments containing the repository path (args.repo)

    Raises:
        Exception: If no playlists are found in the repository
    """

    repository_path = Path(args.repo)
    playlist_paths = _get_playlist_paths(repository_path)
    
    if not playlist_paths:
        raise Exception("No playlist found in repository.")
    
    _display_playlists_header(len(playlist_paths))
    _display_playlists_details(playlist_paths)


def _get_playlist_paths(repository_path: Path) -> List[Path]:
    """
    Retrieve and sort playlist paths from the repository.

    Args:
        repository_path: Path to the repository containing playlists

    Returns:
        List[Path]: Sorted list of playlist paths
    """

    playlist_pattern = re.compile(r"^.*\[(.?[^\]]+)\]$")
    playlist_paths = [
        Path(path) for path in repository_path.glob("*/")
        if playlist_pattern.match(str(path))
    ]
    playlist_paths.sort(key=get_deterministic_sort_key)

    return playlist_paths


def _display_playlists_header(playlist_count: int) -> None:
    """
    Display the header showing the total number of playlists.

    Args:
        playlist_count: Number of playlists found
    """

    print(f"\n{Back.GREEN}{Style.BRIGHT}"
        + f"Found {playlist_count} playlists in repository.{Style.RESET_ALL}")


def _get_playlist_stats(playlist_path: Path) -> PlaylistStats:
    """
    Calculate statistics for a single playlist.

    Args:
        playlist_path: Path to the playlist directory

    Returns:
        PlaylistStats: Statistics about songs in the playlist
    """

    all_songs = list(playlist_path.glob("*.mp3"))
    junk_songs = list(playlist_path.glob("* (JUNK).mp3"))

    return PlaylistStats(len(all_songs), len(junk_songs))


def _display_playlists_details(playlist_paths: List[Path]) -> None:
    """
    Display detailed information for each playlist.

    Args:
        playlist_paths: List of paths to playlist directories
    """
    
    progress_counter = ProgressCounter(len(playlist_paths))
    placeholder = progress_counter.placeholder()
    
    for index, playlist_path in enumerate(playlist_paths, 1):
        counter = progress_counter.format(index)
        playlist_youtube_id = extract_youtube_id_from_filename(playlist_path.name)
        playlist_name = playlist_path.name.replace(f"[{playlist_youtube_id}]", "").strip()
        stats = _get_playlist_stats(playlist_path)
        
        # Display playlist information
        print(f"\n{counter}  "
            + f"{Fore.LIGHTYELLOW_EX}{playlist_name}{Style.RESET_ALL}")
        print(f"{placeholder}  "
            + f"{Fore.CYAN}ID: {Style.DIM}{playlist_youtube_id}{Style.RESET_ALL}")
        
        # Display playlist statistics
        print(f"{placeholder}  {Style.BRIGHT}"
            + f"Number of well tagged songs .... {stats.valid_songs}{Style.RESET_ALL}")
        print(f"{placeholder}  {Style.BRIGHT}"
            + f"Number of junk songs ........... {stats.junk_songs}{Style.RESET_ALL}")
        print(f"{placeholder}  {Fore.LIGHTCYAN_EX}{Style.BRIGHT}"
            + f"Total .......................... {stats.total_songs}{Fore.RESET}")