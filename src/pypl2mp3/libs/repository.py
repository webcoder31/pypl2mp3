#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module handles playlist and song file management within the
repository structure, including retrieval and filtering of song files.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
from __future__ import annotations

import math
import random
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from urllib.parse import parse_qs, urlparse

# Third party packages
from colorama import Back, Fore, Style, init

# pypl2mp3 libs
from pypl2mp3.libs.exceptions import AppBaseException
from pypl2mp3.libs.logger import logger
from pypl2mp3.libs.song import SongModel
from pypl2mp3.libs.utils import (
    get_song_id_from_filename,
    natural_sort_key,
    get_match_score,
)

# Automatically clear style on each print
init(autoreset=True)


class RepositoryException(AppBaseException):
    """
    Custom exception for repository errors.
    """
    pass


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
        SimpleNamespace with playlist details 
            (id, url, exists, folder, path, name)

    Raises:
        RepositoryError: 
            - If playlist ID format is invalid 
            - or provided optional playlist index is out of range 
            - or playlist doesn't exist in the repository when must_exist=True
    """


    def _get_playlist_folders() -> list[str]:
        """
        Get all playlist folders in the repository.

        This function retrieves all folders in the repository that match
        the expected playlist naming convention. The folders are sorted
        by a deterministic key to ensure consistent ordering.
        The naming convention is expected to be: "PlaylistName [YouTubeID]".

        Args:
            repository_path: Path to the repository root

        Returns:
            List of playlist folder names sorted by deterministic key
        """

        return sorted(
            [folder.name for folder in repository_path.glob("*")
             if re.match(r"^.*\[[^\]]+\][^\]]*$", folder.name)],
            key=natural_sort_key
        )


    def _extract_playlist_id(identifier: str) -> str:
        """
        Extract YouTube playlist ID from a URL or ID string.

        Args:
            identifier: YouTube playlist ID or URL

        Returns:
            Extracted playlist ID

        Raises:
            RepositoryError: If the playlist ID format is invalid
        """

        # Try to extract the playlist ID from the identifier handled as a URL
        parsed_url = urlparse(identifier)
        query_params = parse_qs(parsed_url.query)
        playlist_id = query_params.get("list", [None])[0]

        # If the playlist ID is not found in the URL, use the identifier as is
        if playlist_id is None:
            playlist_id = identifier

        # Validate the playlist ID format
        # The ID should be alphanumeric and between 16 to 34 characters long
        # (YouTube playlist IDs are typically 34 characters long)
        if re.match(r"^[A-Za-z0-9_-]{16,34}$", playlist_id) is None:
            raise RepositoryException("Invalid playlist ID format.")

        return playlist_id


    # Get all playlist folders in the repository
    playlist_folders = _get_playlist_folders()
    
    # Handle numeric playlist identifiers (indexes)
    if str(playlist_identifier).isnumeric():
        index = int(playlist_identifier) - 1

        # If playlist index is out of range, raise an error
        if not (0 <= index < len(playlist_folders)):
            raise RepositoryException("Playlist index is out of range.")
        
        # If index is valid, return the corresponding playlist
        folder = playlist_folders[index]
        playlist_id = get_song_id_from_filename(folder)
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
    
    # If multiple folders match the playlist ID, raise an error
    if len(matching_folders) > 1:
        raise RepositoryException(
            "Multiple playlists match YouTube ID in repository."
        )
    
    if not matching_folders:

        # If no matching folders are found 
        # and must_exist is True, raise an error
        if must_exist:
            raise RepositoryException(
                "Expected playlist does not exist in repository."
            )
        
        # If no matching folders are found and must_exist is False, return 
        # a blank playlist object to be used for importing a new playlist
        return SimpleNamespace(
            id=playlist_id,
            url=f"https://www.youtube.com/playlist?list={playlist_id}",
            exists=False,
            folder=None,
            path=None,
            name=None
        )

    # If exactly one matching folder is found, return its details
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
) -> list[Path]:
    """
    Retrieve song files from repository or playlist 
    matching specified criteria.

    Args:
        repository_path: Root path of the repository
        junk_only: If True, only return songs marked as junk
        keywords: Search terms to filter songs
        filter_match_threshold: Minimum match score for keyword filtering
        song_index: Specific song index to retrieve (1-based, 0 for random)
        playlist_identifier: Optional playlist to search within

    Returns:
        List of paths to matching song files or None if no songs are found

    Raises:
        RepositoryError: If provided optional song index is out of range
    """

    search_path = repository_path
    selected_playlist = None

    # If a playlist identifier is provided, retrieve the playlist
    # and set the search path to the playlist folder
    if playlist_identifier:
        selected_playlist = \
            get_repository_playlist(
                repository_path, 
                playlist_identifier, 
                must_exist=True
            )
        search_path = selected_playlist.path

    # Retrieve all song files matching the search criteria
    song_files = _find_matching_songs(
        search_path,
        keywords,
        filter_match_threshold,
        junk_only
    )

    # If no songs are found, return None
    if not song_files:
        return None

    # If a specific song index is provided, filter the list
    if song_index is not None:

        # If song index is out of range, raise an error
        if not (0 <= song_index <= len(song_files)):
            raise RepositoryException("Song index is out of range.")
        
        # If song index is 0, select a random song
        index = random.randint(0, len(song_files) - 1) if song_index == 0 \
            else song_index - 1

        # If a specific song index is provided, 
        # restritc song list to that song
        song_files = [song_files[index]]

    # Return the list of song files
    return song_files


def _find_matching_songs(
    search_path: Path,
    keywords: str = "",
    threshold: float = 45,
    junk_only: bool = False
) -> list[Path]:
    """
    Find and sort song files based on search criteria and match scores.

    This function searches for song files in the specified path,
    filters them based on keywords and match scores, and returns
    a sorted list of matching song file paths. The search can be
    restricted to junk songs only if specified.

    If no keywords are provided, the function will return all
    song files sorted by name. If keywords are provided, the
    function will filter the song files based on normalized match
    score and return only those that meet the specified threshold.

    Args:
        search_path: Path to search for song files
        keywords: Search terms to filter songs
        threshold: Minimum match score for keyword filtering
        junk_only: If True, only return songs marked as junk

    Returns:
        List of paths to matching song files or None if no songs are found
    """
    
    # Get all valid song files with YouTube IDs
    file_pattern = "*(JUNK).mp3" if junk_only else "*.mp3"
    song_files = [
        path for path in search_path.rglob(file_pattern)
            if get_song_id_from_filename(path.name)
    ]

    # If no song files are found, return None
    if not song_files:
        return None

    if not keywords:
        # If no keywords are provided, return songs sorted by name
        return _sort_songs_by_name(song_files)

    # If keywords are provided, return songs filtered and sorted by match score
    return _filter_and_sort_songs_by_match_score(
        song_files, 
        keywords, 
        threshold
    )


def _sort_songs_by_name(song_files: list[Path]) -> list[Path]:
    """
    Sort songs by artist and title.

    Args:
        song_files: List of song file paths

    Returns:
        List of sorted song file paths
    """
    
    # Create a list of song objects with their paths and names
    songs = []
    for path in song_files:
        try:
            song = SongModel(path)
            songs.append({
                "path": path,
                "name": f"{song.artist} - {song.title}"
            })
        except Exception as exc:
            # Handle exceptions when reading song metadata
            logger.error(
                exc, 
                f"Unable to read metadata for song \"{path}\“ - skipping."
            )
            # Skip files that cannot be read as songs
            continue
    
    # Return sorted song paths based on artist and title
    return [
        song["path"] for song in sorted(
            songs,
            key=lambda s: (natural_sort_key(s["name"]), s["path"].parent.name)
        )
    ]


def _filter_and_sort_songs_by_match_score(
    song_files: list[Path],
    keywords: str,
    threshold: float
) -> list[Path]:
    """
    Filter and sort songs based on normalized keyword match scores.

    Args:
        song_files: List of song file paths
        keywords: Search terms to filter songs
        threshold: Minimum match score for keyword filtering

    Returns:
        List of filtered and sorted song file paths
    """
    
    # Create a list of song objects with their paths and match scores
    matched_songs = []
    for path in song_files:
        try:
            song = SongModel(path)
            match_level = get_match_score(song.artist, song.title, keywords)
            if match_level > 0:
                matched_songs.append({"path": path, "match_level": match_level})
        except Exception as exc:
            # Handle exceptions when reading song metadata
            logger.error(
                exc, 
                f"Unable to read metadata for song \"{path}\“ - skipping."
            )
            # Skip files that cannot be read as songs
            continue

    if not matched_songs:
        # If no songs match the criteria, return None
        return None

    # if songs match the criteria, return them filterd 
    # and sorted by normalized match score
    return _normalize_and_filter_song_matches(matched_songs, threshold)


def _normalize_and_filter_song_matches(
    matched_songs: list[dict],
    threshold: float
) -> list[Path]:
    """
    Normalize song match scores and filter based on threshold.

    Args:
        matched_songs: List of matched songs with scores to normalize
        threshold: Minimum normalized score for final filtering

    Returns:
        List of filtered song file paths sorted by match score 
        or None if no matches
    """

    # First, sort matched songs by match level in descending order
    # to preserve the original order for normalization
    matched_songs.sort(key=lambda s: s["match_level"], reverse=True)
    
    # Calculate the minimum and maximum match scores
    # and the range of scores for normalization
    scores = [song["match_level"] for song in matched_songs]
    min_score = min(scores)
    score_range = max(scores) - min_score

    # Normalize match scores to a 0-100 range
    for song in matched_songs:
        raw_score = \
            song["match_level"] - (min_score if score_range > 0 else 0)
        song["match_level"] = \
            (math.sqrt(raw_score) / math.sqrt(score_range or 1)) * 100

    # Return songs that meet the threshold criteria
    matching_songs = [
        song["path"] for song in matched_songs
        if song["match_level"] >= threshold
    ]

    # If no songs match the criteria, return None
    if not matching_songs:
        return None
    
    # If songs match the criteria, return them sorted by match score
    return matching_songs
        