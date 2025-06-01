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


# ------------------------
# Constants
# ------------------------

# Match thresholds for filtering
DEFAULT_FILTER_THRESHOLD = 45.0  # Default minimum match score for keyword filtering
MIN_MATCH_THRESHOLD = 0.0        # Minimum allowed match threshold
MAX_MATCH_THRESHOLD = 100.0      # Maximum allowed match threshold

# ------------------------
# Exceptions
# ------------------------

class RepositoryException(AppBaseException):
    """
    Exception raised for repository-specific errors.
    
    This custom exception type helps distinguish repository-related errors
    from other application errors, enabling more specific error handling.
    Common scenarios include:
    - Invalid playlist IDs
    - Missing playlists/songs
    - Out of range indices
    - Multiple matching playlists
    """
    pass


# ------------------------
# Public Functions
# ------------------------

def get_repository_playlist(
    repository_path: Path,
    playlist_identifier: str,
    must_exist: bool = True
) -> SimpleNamespace:
    """
    Retrieve and validate playlist information from an identifier.

    Takes a playlist identifier (ID, URL, or index) and returns detailed
    playlist information. Handles validation and existence checking.

    Args:
        repository_path (Path): Root directory path for the repository
        playlist_identifier (str): YouTube playlist ID, URL, or index number
        must_exist (bool, optional): If True, raises error when playlist
            isn't found. Defaults to True.

    Returns:
        SimpleNamespace: Playlist details containing:
            - id (str): YouTube playlist ID
            - url (str): Full YouTube playlist URL
            - exists (bool): Whether playlist exists in repository
            - folder (str | None): Folder name if exists, else None
            - path (Path | None): Full folder path if exists, else None
            - name (str | None): Display name if exists, else None

    Raises:
        RepositoryException: When:
            - Playlist ID format is invalid (not 16-34 alphanumeric chars)
            - Provided playlist index is out of range
            - Playlist doesn't exist in repository (if must_exist=True)
            - Multiple playlists match the same ID
    """


    def _get_playlist_folders() -> list[str]:
        """
        Find and sort playlist folders in the repository.

        Scans the repository directory for folders matching the playlist
        naming pattern: "PlaylistName [YouTubeID]". Only matches properly
        formatted folders with bracketed YouTube IDs.

        The folders are sorted using natural_sort_key() for consistent,
        human-friendly ordering that:
        - Handles numbers properly ("2" before "10")
        - Is case-insensitive
        - Normalizes special characters

        Returns:
            list[str]: Playlist folder names in sorted order
        """

        return sorted(
            [folder.name for folder in repository_path.glob("*")
             if re.match(r"^.*\[[^\]]+\][^\]]*$", folder.name)],
            key=natural_sort_key
        )


    def _extract_playlist_id(identifier: str) -> str:
        """
        Extract and validate YouTube playlist ID.

        Handles two input formats:
        1. Raw ID string (16-34 alphanumeric chars)
        2. YouTube URL with 'list' parameter

        Enforces ID format rules:
        - Length: 16-34 characters
        - Content: Only letters, numbers, hyphens, underscores
        - No spaces or special characters

        Args:
            identifier (str): YouTube playlist ID or URL
                Examples:
                - "PLH6pfGXX1JvLxWqCdgdj2QyR"
                - "https://youtube.com/playlist?list=PLH6pfGXX1JvLxWqCdgdj2QyR"

        Returns:
            str: Validated YouTube playlist ID

        Raises:
            RepositoryException: If playlist ID is invalid:
                - Wrong length (not 16-34 chars)
                - Invalid characters
                - Malformed URL
                - Missing playlist ID
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
            f"Multiple playlists match YouTube ID \"{playlist_id}\" in repository."
        )
    
    if not matching_folders:

        # If no matching folders are found 
        # and must_exist is True, raise an error
        if must_exist:
            raise RepositoryException(
                f"Expected playlist \"{playlist_id}\" does not exist in repository."
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
    filter_match_threshold: float = DEFAULT_FILTER_THRESHOLD,
    song_index: Optional[int] = None,
    playlist_identifier: Optional[str] = None,
) -> list[Path] | None:
    """
    Search and retrieve song files matching specified criteria.

    Performs a flexible search across the repository or within a specific playlist,
    with support for filtering by keywords, junk status, and specific indices.
    Uses fuzzy string matching for keyword filtering with customizable threshold.

    Args:
        repository_path (Path): Root path of the repository
        junk_only (bool, optional): If True, only return songs marked as junk.
            Defaults to False.
        keywords (str, optional): Search terms to filter songs. Defaults to "".
        filter_match_threshold (float, optional): Minimum match score (0-100)
            for keyword filtering. Defaults to DEFAULT_FILTER_THRESHOLD.
        song_index (Optional[int], optional): Specific song index to retrieve.
            1-based indexing, 0 for random selection. Defaults to None.
        playlist_identifier (Optional[str], optional): Limit search to this
            playlist. Accepts ID, URL or index. Defaults to None.

    Returns:
        list[Path] | None: List of paths to matching song files, or None if
            no matches found. Files are ordered by:
            - Match score (if keywords provided)
            - Artist/title (if no keywords)

    Raises:
        RepositoryException: When provided song index is out of range
        ValueError: When filter_match_threshold is not between 0 and 100
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
            raise RepositoryException(f"Song index \"{song_index}\" is out of range.")
        
        # If song index is 0, select a random song
        index = random.randint(0, len(song_files) - 1) if song_index == 0 \
            else song_index - 1

        # If a specific song index is provided, 
        # restritc song list to that song
        song_files = [song_files[index]]

    # Return the list of song files
    return song_files


# ------------------------
# Private Helper Functions
# ------------------------

def _find_matching_songs(
    search_path: Path,
    keywords: str = "",
    threshold: float = DEFAULT_FILTER_THRESHOLD,
    junk_only: bool = False
) -> list[Path] | None:
    """
    Find and sort songs matching given criteria.

    Performs a comprehensive song search and scoring operation:
    1. Collects all MP3 files in the search path
    2. Filters for valid YouTube song IDs
    3. When keywords provided:
       - Calculates match scores against artist/title
       - Normalizes scores to 0-100 range
       - Filters by threshold
       - Sorts by match score
    4. When no keywords:
       - Sorts by artist/title naturally

    Args:
        search_path (Path): Directory to search for songs
        keywords (str, optional): Search terms to filter songs. Defaults to "".
        threshold (float, optional): Minimum normalized match score (0-100)
            for inclusion. Defaults to 45.0.
        junk_only (bool, optional): Only include songs marked as junk.
            Defaults to False.

    Returns:
        list[Path] | None: Sorted list of matching song paths, or None if no
            matches found

    Note:
        The scoring algorithm uses fuzzy string matching and square root
        normalization to provide intuitive relative rankings.
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
    Sort songs naturally by artist and title.

    Creates composite sort keys from artist and title metadata for each song,
    then performs a natural sort that handles numbers intelligently.
    Falls back to parent folder name as secondary sort key.

    Args:
        song_files (list[Path]): List of song file paths to sort

    Returns:
        list[Path]: Songs sorted by "Artist - Title", then by folder name
        
    Note:
        Songs with unreadable metadata are logged and skipped. The natural
        sort handles cases like "Track 2" vs "Track 10" correctly.
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
) -> list[Path] | None:
    """
    Filter and rank songs by keyword match relevance.

    Two-step process:
    1. Initial scoring:
       - Reads metadata for each song
       - Calculates raw match scores against keywords
       - Retains songs with non-zero scores
    2. Score processing:
       - Normalizes scores to 0-100 range
       - Filters by threshold
       - Sorts by final score

    Args:
        song_files (list[Path]): Songs to process
        keywords (str): Search terms to match against
        threshold (float): Minimum normalized score (0-100) for inclusion

    Returns:
        list[Path] | None: Ranked list of matching songs, or None if no matches
        
    Note:
        Uses fuzzy string matching to handle minor variations in spelling and
        word order. The normalization ensures consistent scoring across different
        keyword sets.
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
    matched_songs: list[dict[str, Path | float]],
    threshold: float
) -> list[Path] | None:
    """
    Normalize match scores and apply threshold filtering.

    Implements score normalization algorithm:
    1. Orders matches by raw score to preserve ranking
    2. Calculates score range and minimum
    3. Applies square root normalization to compress range:
       normalized = √(raw - min) / √(range) * 100
    4. Filters by normalized threshold
    
    Args:
        matched_songs (list[dict[str, Path | float]]): Songs with raw scores.
            Each dict must have 'path' and 'match_level' keys.
        threshold (float): Minimum normalized score (0-100) to retain

    Returns:
        list[Path] | None: Filtered and sorted song paths, or None if no matches
        
    Note:
        The square root normalization helps emphasize relative differences
        between closely matched songs while compressing larger gaps.
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
        