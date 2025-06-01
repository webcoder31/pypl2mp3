#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module provides core utility functions used throughout the application:
- Text formatting and styling utilities
- YouTube ID extraction from URLs and filenames
- Fuzzy text matching and scoring
- Natural sorting for deterministic ordering
- User interaction helpers

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
from dataclasses import dataclass
import math
import re
from typing import Optional, TypeVar, Union, Any
from pathlib import Path

# Third party packages
from colorama import Back, Fore, Style
from slugify import slugify
from thefuzz import fuzz

# ------------------------
# Type Definitions
# ------------------------

T = TypeVar('T')
SongType = TypeVar('SongType')  # For functions expecting a SongModel instance

# ------------------------
# Constants
# ------------------------

# Fuzzy matching configuration
DEFAULT_MATCH_THRESHOLD = 45.0  # Default minimum match score
KEYWORD_PENALTY_FACTOR = 10     # Penalty multiplier for each unmatched keyword
MIN_FUZZY_SCORE = 10            # Minimum score to consider a fuzzy match

# Display formatting
DEFAULT_LABEL_WIDTH = 33        # Default width for labels
MIN_NUMBER_WIDTH = 2            # Minimum width for counter digits

# ------------------------
# Formatting Classes
# ------------------------

@dataclass
class LabelFormatter:
    """
    Formats text labels with consistent width and styling.

    Provides utilities for left-justified text labels with optional styling:
    - format(): Adds styling (dim white text) and padding
    - pad_only(): Adds just padding without styling

    Args:
        width (int): Width to pad labels to. Labels longer than this will
            not be truncated.
    """
    
    width: int

    def format(self, label: str) -> str:
        """
        Format a label with consistent width and dim white styling.
        
        Args:
            label (str): Text to format
            
        Returns:
            str: Formatted label with padding and styling
        """

        return (
            f"{Fore.WHITE}{Style.DIM}"
            f"{label.ljust(self.width)}"
            f"{Style.RESET_ALL}"
        )
    

    def pad_only(self, label: str) -> str:
        """
        Format a label with consistent width but no styling.
        
        Args:
            label (str): Text to format
            
        Returns:
            str: Label padded to specified width
        """

        return f"{label.ljust(self.width)}"


@dataclass
class CountFormatter:
    """
    Format numeric counters with consistent styling and width.

    Creates consistently formatted progress counters (e.g., "01/10") with:
    - Fixed width based on total count
    - Zero-padding for single digit numbers
    - Color coding (bright blue for current, dim blue for total)
    - Optional placeholder text for empty slots

    Args:
        total_count (int): Maximum count value (determines width)
    """
    
    total_count: int
    
    def __post_init__(self) -> None:
        """
        Initialize width calculations after instance creation.

        Calculates:
        - number_width: Width for each number (current/total)
        - width: Total width including separator
        """
        self.number_width = max(MIN_NUMBER_WIDTH, len(str(self.total_count)))
        self.width = self.number_width * 2 + 1

    def format(self, current: int) -> str:
        """
        Format a progress counter with consistent styling.
        
        Creates a counter string with:
        - Zero-padded numbers
        - Bright blue for current count
        - Dim blue for total count
        - Fixed width based on total_count
        
        Args:
            current (int): Current count to display
            
        Returns:
            str: Formatted counter string (e.g., "07/15")

        Note:
            Width is calculated to accommodate the largest possible value
            to prevent alignment issues as the counter increases.
        """
        
        return (
            f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}" 
            f"{str(current).rjust(self.number_width, '0')}"
            f"{Style.DIM}/{Style.RESET_ALL}{Fore.BLUE}"
            f"{str(self.total_count).rjust(self.number_width, '0')}"
            f"{Style.RESET_ALL}"
        )
    

    def placeholder(self, text: str = "") -> str:
        """
        Create a placeholder matching counter width.
        
        Useful for consistent alignment in lists where some items
        don't have counters. Text is truncated if longer than
        counter width.
        
        Args:
            text (str, optional): Text to display in placeholder space.
                Will be truncated if longer than counter width.
                Defaults to empty string.
            
        Returns:
            str: Blue-colored text padded to counter width
        """

        return (
            f"{Fore.LIGHTBLUE_EX}" 
            f"{text[:self.width].ljust(self.width)}"
            f"{Style.RESET_ALL}"
        )


# ------------------------
# ID Extraction Functions
# ------------------------

def get_song_id_from_filename(filename: Union[str, Path]) -> Optional[str]:
    """
    Extract YouTube video ID from a song filename.

    Looks for ID in the last set of square brackets in the filename.

    Follows naming convention: 
    - "Title [YoutubeID].mp3"
    - "Title [YoutubeID] (JUNK).mp3"

    Args:
        filename (Union[str, Path]): Path or name of the song file.
            Can handle:
            - Full paths
            - Just filenames
            - With or without extension
            - Multiple bracketed sections

    Returns:
        Optional[str]: YouTube video ID if found in brackets,
            None if no valid ID format found

    Example:
        >>> get_song_id_from_filename("My Song [dQw4w9WgXcQ].mp3")
        'dQw4w9WgXcQ'
        >>> get_song_id_from_filename("Preview [Demo] [dQw4w9WgXcQ] (JUNK).mp3")
        'dQw4w9WgXcQ'  # Takes last bracketed section
        >>> get_song_id_from_filename("Invalid.mp3")
        None
        
    Note:
        The ID extraction is format-agnostic - it will return any text
        in the last brackets without validating if it's a real YouTube ID.
        Use in conjunction with validation functions if needed.
    """

    pattern = r'^.*\[(?P<youtube_id>[^\]]+)\][^\]]*$'

    if match := re.match(pattern, str(filename)):
        return match.group('youtube_id')
    
    return None


def get_song_id_from_url(url: str) -> Optional[str]:
    """
    Extract video ID from a YouTube URL.

    Currently supports basic format: "anything=VIDEO_ID"
    Future enhancement: Add support for other YouTube URL formats:
    - youtube.com/watch?v=ID
    - youtu.be/ID
    - youtube.com/v/ID
    - youtube.com/embed/ID

    Args:
        url (str): YouTube URL containing video ID after '='
            Example: "https://youtube.com/watch?v=dQw4w9WgXcQ"

    Returns:
        Optional[str]: YouTube video ID if found, None if invalid URL format

    Example:
        >>> get_song_id_from_url("https://youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
        >>> get_song_id_from_url("https://example.com")
        None
        
    Note:
        Like get_song_id_from_filename(), this function only extracts the ID
        without validating if it's a legitimate YouTube video ID. Additional
        validation should be performed if needed.
    """

    pattern = r'^.*=(?P<youtube_id>.+)$'

    if match := re.match(pattern, str(url)):
        return match.group('youtube_id')
    
    return None


# ------------------------
# Search and Matching Functions
# ------------------------

def get_match_score(artist: str, title: str, keywords: str) -> float:
    """
    Calculate similarity score between song metadata and search terms.

    Uses a multi-step scoring algorithm:
    1. Direct keyword matching against combined artist/title
    2. Fuzzy matching for partial/misspelled matches
    3. Progressive weighting for multi-keyword searches
    4. Penalty system for non-matching keywords
    5. Score normalization and thresholding

    Args:
        artist (str): Song artist name
        title (str): Song title
        keywords (str): Space-separated search terms

    Returns:
        float: Match score from 0-100, where:
            100 = Perfect match
            0-99 = Partial match (higher is better)
            0 = No match

    Example:
        >>> get_match_score("The Beatles", "Hey Jude", "beatles jude")
        100.0
        >>> get_match_score("The Beatles", "Hey Jude", "beattles")
        85.7  # Fuzzy match on misspelling
    
    Notes:
        - Matching is case-insensitive
        - Word order matters (first get more weight)
        - Uses exponential penalty for multiple non-matching keywords
        - Perfect matches on artist name weighted less than title
    """

    # If no keywords are provided, return a perfect score
    if not keywords:
        return 100.0

    song_name = f'{artist.lower()} {title.lower()}'.strip()
    keyword_list = keywords.lower().split()
    
    score = 0.0
    weak_match_penalty = 0
    keyword_acc = ''
    weight = len(keyword_list)
    weight_sum = sum(range(1, weight + 1))
    
    # Score calculation combines exact and fuzzy matching:
    # 1. Process each keyword with decreasing weight (most important first)
    # 2. For each keyword:
    #    - Check for exact substring match (100 points * weight)
    #    - If no exact match, calculate fuzzy score:
    #      * Compare accumulated keywords against artist (20% weight)
    #      * Compare against title (20% weight)
    #      * Compare against full name (60% weight)
    #    - Apply penalty for poor fuzzy matches
    for keyword in keyword_list:
        # Build cumulative keyword phrase
        keyword_acc = f'{keyword_acc} {keyword}'.strip()
        
        if keyword in song_name:
            # Exact match gets full points weighted by position
            score += 100 * weight
        else:
            # Weighted average of fuzzy matches:
            # - artist (1x weight): Check artist name separately
            # - title (1x weight): Check title separately
            # - full name (3x weight): Check combined for context
            fuzzy_score = (
                fuzz.WRatio(keyword_acc, artist.lower()) +  # 20%
                fuzz.WRatio(keyword_acc, title.lower()) +   # 20%
                3 * fuzz.WRatio(keyword_acc, song_name)     # 60%
            ) / 5
            
            # Apply penalty if fuzzy match is too weak
            # Threshold decreases with more keywords
            if fuzzy_score < 100 - (10 * len(keyword_list)):
                weak_match_penalty += weight
            score += fuzzy_score * weight
        
        weight -= 1  # Decrease weight for next keyword
    
    # Calculate length penalty to favor specific searches:
    # Uses exponential decay to reduce score as keyword count increases:
    # penalty = 50 * e^(-ln(2)/3 * weight_sum)
    # This gives approximately:
    # - 1 keyword:  25 point penalty
    # - 2 keywords: 20 point penalty
    # - 3 keywords: 16 point penalty
    # - 4 keywords: 13 point penalty
    # Prevents long queries from artificially inflating scores
    query_length_penalty = 50 * math.exp(-(math.log(2) / 3) * weight_sum)

    # Final score calculation:
    # 1. Normalize raw score by total possible weight
    # 2. Subtract length penalty to favor specific searches
    # 3. Subtract accumulated penalties for poor matches
    final_score = (score / weight_sum) \
        - query_length_penalty \
        - (weak_match_penalty * KEYWORD_PENALTY_FACTOR)
    
    # Ensure non-negative result
    return max(final_score, 0.0)


def natural_sort_key(key: str) -> tuple[str, str]:
    """
    Create case-insensitive natural sort key for text.

    Generates a tuple of (normalized, original) keys for stable sorting that:
    - Ignores case
    - Removes diacritics
    - Handles numbers naturally (e.g., "2" < "10")
    - Preserves original string for display

    Args:
        key (str): Text to create sort key for

    Returns:
        tuple[str, str]: (normalized_key, original_key) where:
            normalized_key: Lowercase, unaccented version for sorting
            original_key: Original string preserved for display

    Example:
        >>> sorted([("10.mp3"), ("2.mp3")], key=natural_sort_key)
        ['2.mp3', '10.mp3']  # Numbers sorted naturally
        >>> sorted(["é.txt", "e.txt"], key=natural_sort_key)
        ['e.txt', 'é.txt']   # Diacritics normalized
    """

    return slugify(str(key)).casefold(), str(key)


# ------------------------
# User Interaction Functions
# ------------------------

def prompt_user(question: str, options: list[str]) -> str:
    """
    Display a styled prompt with multiple choice options (case-insensitive).

    Args:
        question (str): Question text to display
        options (list[str]): Valid response options

    Returns:
        str: User's response in lowercase

    Example:
        >>> response = prompt_user("Proceed", ["yes", "no", "retry"])
        Proceed (yes/no/retry) ?  # Displays with colors
        >>> response == "yes"
        True
    """

    formatted_options = [
        f"{Fore.CYAN}{opt}{Fore.RESET}" for opt in options
    ]
    return input(
        f"{Style.BRIGHT}{Fore.WHITE}"
        f"{question}{Fore.RESET} " 
        f"({'/'.join(formatted_options)}) ? "
    ).lower()


def check_and_display_song_selection_result(songs: list[SongType]) -> None:
    """
    Display song search results with visual feedback.

    Shows a colored banner indicating:
    - Yellow: Songs found (shows count)
    - Magenta: No matches found (exits program)

    Args:
        songs (list[SongType]): List of found song objects

    Raises:
        SystemExit: When no songs are found
    """
    
    songCount = len(songs) if songs else 0
    if songCount > 0:
        print(
            f"\n{Back.YELLOW}{Style.BRIGHT}" 
            f" Found {len(songs)} songs matching selection criteria "
            f"{Style.RESET_ALL}"
        )
    else:
        print(
            f"\n{Back.MAGENTA}{Style.BRIGHT}" 
            f" No songs match the selection criteria "
            f"{Style.RESET_ALL}"
        )
        raise SystemExit("No songs match the selection criteria")


def format_song_display(song: SongType, counter: str) -> str:
    """
    Format a song entry for list display with colors.

    Creates a formatted and styled line like:
    ```
    01/10  03:45  Artist Name  Song Title  (JUNK)
    ```

    Args:
        song (SongType): Song object with required attributes:
            - duration (str): Song length (e.g., "03:45")
            - artist (str): Artist name
            - title (str): Song title
            - has_junk_filename (bool): Whether marked as junk
        counter (str): Position display (e.g., "01/10")

    Returns:
        str: Formatted and colored song entry
    """

    junk_indicator = "  (JUNK)" if song.has_junk_filename else ""
    
    return (
        f"{counter}  "
        f"{Fore.WHITE}{song.duration}  "
        f"{Style.BRIGHT}"
        f"{Fore.LIGHTGREEN_EX}{song.artist}  "
        f"{Fore.LIGHTYELLOW_EX}{song.title}"
        f"{Fore.MAGENTA}{junk_indicator}"
        f"{Style.RESET_ALL}"
    )


def format_song_details_display(
        song: SongType,
        count_formatter: CountFormatter
    ) -> str:
    """
    Format detailed song information for display.

    Creates a multi-line display like:
    ```
    ...  Playlist: My Playlist
    ...  Filename: Song.mp3
    ...  Link: https://youtu.be/dQw4w9WgXcQ
    ```
    All fields are color-coded and aligned with proper spacing.

    Args:
        song (SongType): Song object with required attributes:
            - playlist (str): Playlist name
            - filename (str): Full filename
            - youtube_id (str): YouTube video ID
        count_formatter (CountFormatter): For consistent number formatting

    Returns:
        str: Multi-line formatted details
    """
    
    label_formatter = LabelFormatter(9)
    placeholder = count_formatter.placeholder()
    
    fields = {
        "Playlist": song.playlist,
        "Filename": song.filename,
        "Link": f"https://youtu.be/{song.youtube_id}"
    }
    
    items = []
    for label, value in fields.items():
        items.append(
            f"{placeholder}  "
            f"{label_formatter.format(label)}"
            f"{Fore.LIGHTBLUE_EX}{value}{Style.RESET_ALL}"
        )

    return "\n".join(items)
