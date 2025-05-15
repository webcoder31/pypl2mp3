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

# Third party packages
from colorama import Fore, Back, Style, init

# pypl2mp3 libs
from pypl2mp3.libs.utils import (
    CountFormatter, 
    natural_sort_key, 
    get_song_id_from_filename
)

# Automatically clear style on each print
init(autoreset=True)


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


def list_playlists(args: any) -> None:
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
        print(f"{Back.MAGENTA}{Style.BRIGHT}"
            + f" No playlists found in repository ")
        return
    else:
        print(f"\n{Back.YELLOW}{Style.BRIGHT}"
            + f" Found {len(playlist_paths)} playlists in repository. ")
    
    _display_playlists_details(playlist_paths)


def _get_playlist_paths(repository_path: Path) -> list[Path]:
    """
    Retrieve and sort playlist paths from the repository.

    Args:
        repository_path: Path to the repository containing playlists

    Returns:
        list[Path]: Sorted list of playlist paths
    """

    playlist_pattern = re.compile(r"^.*\[(.?[^\]]+)\]$")
    playlist_paths = [
        Path(path) for path in repository_path.glob("*/")
        if playlist_pattern.match(str(path))
    ]
    playlist_paths.sort(key=natural_sort_key)

    return playlist_paths


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


def _display_playlists_details(playlist_paths: list[Path]) -> None:
    """
    Display detailed information for each playlist.

    Args:
        playlist_paths: List of paths to playlist directories
    """
    
    count_formatter = CountFormatter(len(playlist_paths))
    placeholder = count_formatter.placeholder()
    
    for index, path in enumerate(playlist_paths, 1):
        counter = count_formatter.format(index)
        playlist_id = get_song_id_from_filename(path.name)
        playlist_name = path.name.replace(f"[{playlist_id}]", "").strip()
        stats = _get_playlist_stats(path)
        
        # Display playlist information
        print(
            f"\n{counter}  "
            f"{Fore.LIGHTYELLOW_EX}{playlist_name}"
        )
        print(
            f"{placeholder}  "
            f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}ID: {Style.NORMAL}{playlist_id}"
        )
        
        # Display playlist statistics
        print(
            f"{placeholder}  {Style.BRIGHT}"
            f"Number of well tagged songs .... {stats.valid_songs}"
        )
        print(
            f"{placeholder}  {Style.BRIGHT}"
            f"Number of junk songs ........... {stats.junk_songs}"
        )
        print(
            f"{placeholder}  {Fore.LIGHTGREEN_EX}{Style.BRIGHT}"
            f"Total .......................... {stats.total_songs}"
        )