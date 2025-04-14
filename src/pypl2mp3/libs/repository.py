#!/usr/bin/env python3

"""
This file is part of PYPL2MP3 software, 
a YouTube playlist MP3 converter that can also shazam, tag and play songs.

@author    Thierry Thiers <webcoder31@gmail.com>
@copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
@license   http://www.cecill.info  CeCILL-C License
@link      https://github.com/webcoder31/pypl2mp3

This module handles playlist and song file management within the repository structure.
"""

# Python core modules
from __future__ import annotations

import math
import random
import re
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional

# Third party packages
from colorama import Back, Fore, Style

# pypl2mp3 libs
from pypl2mp3.libs.song import SongModel, SongError
from pypl2mp3.libs.utils import (
    extract_youtube_id_from_filename,
    get_deterministic_sort_key,
    calculate_fuzzy_match_score,
)


def get_repository_playlist(
    repository_path: Path,
    playlist_identifier: str,
    must_exist: bool = True
) -> SimpleNamespace:
    """
    Retrieve playlist information from a playlist identifier.

    Args:
        repository_path: Path to the repository root
        playlist_identifier: YouTube playlist ID, URL, or index number
        must_exist: If True, raises error when playlist isn't found

    Returns:
        SimpleNamespace containing playlist details (id, url, exists, folder, path, name)

    Raises:
        SongError: If playlist index is invalid or playlist doesn't exist when must_exist=True
    """
    def _get_playlist_folders() -> List[str]:
        return sorted(
            [folder.name for folder in repository_path.glob("*")
             if re.match(r"^.*\[[^\]]+\][^\]]*$", folder.name)],
            key=get_deterministic_sort_key
        )

    def _extract_playlist_id(identifier: str) -> str:
        match = re.match(r"[&?]list=(?P<id>[^&]+)", identifier, re.IGNORECASE)
        return match.group("id") if match else identifier

    playlist_folders = _get_playlist_folders()
    
    # Handle numeric playlist identifiers (indexes)
    if str(playlist_identifier).isnumeric():
        index = int(playlist_identifier) - 1
        if not (0 <= index < len(playlist_folders)):
            raise SongError("Playlist index is out of range.")
        
        folder = playlist_folders[index]
        playlist_id = extract_youtube_id_from_filename(folder)
        return SimpleNamespace(
            id=playlist_id,
            url=f"https://www.youtube.com/playlist?list={playlist_id}",
            exists=True,
            folder=folder,
            path=repository_path / folder,
            name=folder[:-len(playlist_id)-3]
        )

    # Handle YouTube playlist IDs or URLs
    playlist_id = _extract_playlist_id(str(playlist_identifier))
    matching_folders = [
        folder for folder in playlist_folders
        if playlist_id in folder
    ]
    
    if len(matching_folders) > 1:
        raise SongError("Multiple playlists match YouTube ID in repository.")
    
    if not matching_folders:
        if must_exist:
            raise SongError("Playlist does not exist in repository.")
        return SimpleNamespace(
            id=playlist_id,
            url=f"https://www.youtube.com/playlist?list={playlist_id}",
            exists=False,
            folder=None,
            path=None,
            name=None
        )

    folder = matching_folders[0]
    return SimpleNamespace(
        id=playlist_id,
        url=f"https://www.youtube.com/playlist?list={playlist_id}",
        exists=True,
        folder=folder,
        path=repository_path / folder,
        name=folder[:-len(playlist_id)-3]
    )


def get_repository_song_files(
    repository_path: Path,
    junk_only: bool = False,
    keywords: str = "",
    filter_match_threshold: float = 45,
    song_index: Optional[int] = None,
    playlist_identifier: Optional[str] = None,
    display_summary: bool = False
) -> List[Path]:
    """
    Retrieve song files from repository or playlist matching specified criteria.

    Args:
        repository_path: Root path of the repository
        junk_only: If True, only return songs marked as junk
        keywords: Search terms to filter songs
        filter_match_threshold: Minimum match score for keyword filtering
        song_index: Specific song index to retrieve (1-based, 0 for random)
        playlist_identifier: Optional playlist to search within
        display_summary: If True, print search criteria and results

    Returns:
        List of paths to matching song files

    Raises:
        SongError: If no songs are found or index is out of range
    """
    search_path = repository_path
    selected_playlist = None

    if playlist_identifier:
        selected_playlist = get_repository_playlist(repository_path, playlist_identifier, must_exist=True)
        search_path = selected_playlist.path

    song_files = _find_matching_songs(
        search_path,
        keywords,
        filter_match_threshold,
        junk_only
    )

    if not song_files:
        raise SongError("No songs found.")

    if song_index is not None:
        if abs(song_index) > len(song_files):
            raise SongError("Song index is out of range.")
        index = random.randint(0, len(song_files) - 1) if song_index == 0 else song_index - 1
        song_files = [song_files[index]]

    if display_summary:
        _display_search_summary(
            len(song_files),
            selected_playlist,
            keywords,
            filter_match_threshold
        )

    return song_files


def _find_matching_songs(
    search_path: Path,
    keywords: str = "",
    threshold: float = 45,
    junk_only: bool = False
) -> List[Path]:
    """
    Find and sort song files based on search criteria and match scores.
    """
    file_pattern = "*(JUNK).mp3" if junk_only else "*.mp3"
    
    # Get all valid song files with YouTube IDs
    song_files = [
        path for path in search_path.rglob(file_pattern)
        if extract_youtube_id_from_filename(path.name)
    ]

    if not keywords:
        return _sort_songs_by_name(song_files)

    return _filter_and_sort_by_match_score(song_files, keywords, threshold)


def _sort_songs_by_name(song_files: List[Path]) -> List[Path]:
    """
    Sort songs by artist and title.
    """
    songs = []
    for path in song_files:
        try:
            song = SongModel(path)
            songs.append({
                "path": path,
                "name": f"{song.artist} - {song.title}"
            })
        except Exception:
            continue
    
    return [
        song["path"] for song in sorted(
            songs,
            key=lambda s: (get_deterministic_sort_key(s["name"]), s["path"].parent.name)
        )
    ]


def _filter_and_sort_by_match_score(
    song_files: List[Path],
    keywords: str,
    threshold: float
) -> List[Path]:
    """
    Filter and sort songs based on keyword match scores.
    """
    matched_songs = []
    
    for path in song_files:
        try:
            song = SongModel(path)
            match_level = calculate_fuzzy_match_score(song.artist, song.title, keywords)
            if match_level > 0:
                matched_songs.append({"path": path, "match_level": match_level})
        except Exception:
            continue

    if not matched_songs:
        return []

    return _normalize_and_filter_matches(matched_songs, threshold)


def _normalize_and_filter_matches(
    matched_songs: List[dict],
    threshold: float
) -> List[Path]:
    """
    Normalize match scores and filter based on threshold.
    """
    matched_songs.sort(key=lambda s: s["match_level"], reverse=True)
    
    scores = [song["match_level"] for song in matched_songs]
    min_score = min(scores)
    score_range = max(scores) - min_score

    for song in matched_songs:
        raw_score = song["match_level"] - (min_score if score_range > 0 else 0)
        song["match_level"] = (math.sqrt(raw_score) / math.sqrt(score_range or 1)) * 100

    return [
        song["path"] for song in matched_songs
        if song["match_level"] >= threshold
    ]


def _display_search_summary(
    song_count: int,
    playlist: Optional[SimpleNamespace],
    keywords: str,
    threshold: float
) -> None:
    """
    Display search results summary.
    """
    print(f"\n{Back.YELLOW + Style.BRIGHT} Found {song_count} songs matching criteria {Style.RESET_ALL}\n")
    
    if playlist:
        print(f"{Fore.WHITE + Style.DIM} ⇨ Playlist:   {Style.RESET_ALL}"
              f"{Fore.LIGHTBLUE_EX}{playlist.name}{Fore.RESET}")
    else:
        print(f"{Fore.WHITE + Style.DIM} ⇨ Playlists:  {Style.RESET_ALL}"
              f"{Fore.LIGHTBLUE_EX}ALL{Fore.RESET}")

    if keywords:
        print(f"{Fore.WHITE + Style.DIM} ⇨ Filter:     {Style.RESET_ALL}"
              f"{Fore.LIGHTBLUE_EX}{keywords}  "
              f"{Style.DIM}(match threshold: {threshold}%){Fore.RESET + Style.RESET_ALL}")
    else:
        print(f"{Fore.WHITE + Style.DIM} ⇨ Filter:     {Style.RESET_ALL}"
              f"{Fore.LIGHTBLUE_EX}NONE{Fore.RESET}")
        