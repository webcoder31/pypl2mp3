#!/usr/bin/env python3
"""
PYPL2MP3: YouTube playlist MP3 converter and player,
with Shazam song identification and tagging capabilities.

This module provides utility functions for YouTube ID extraction, 
match score calculation, deterministic sorting and formatting operations.

Copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
License: CeCILL-C (http://www.cecill.info)
Repository: https://github.com/webcoder31/pypl2mp3
"""

# Python core modules
from dataclasses import dataclass
import math
import re
from typing import Optional

# Third party packages
from colorama import Back, Fore, Style
from slugify import slugify
from thefuzz import fuzz


@dataclass
class LabelFormatter:
    """
    Utility class for formatting left-justified labels.
    """
    
    width: int
    

    def format(self, label: str) -> str:
        """
        Format a label with consistent width and styling.
        
        Args:
            label: Label text to format

        Returns:
            Formatted label string
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
            label: Label text

        Returns:
            Right-padded label
        """

        return f"{label.ljust(self.width)}"


@dataclass
class CountFormatter:
    """
    Utility class for formatting progress counters.
    """
    
    total_count: int
    

    def __post_init__(self):
        self.number_width = max(2, len(str(self.total_count)))
        self.width = self.number_width * 2 + 1
    

    def format(self, current: int) -> str:
        """
        Format a progress counter (e.g., '01/10').
        
        Args:
            current: Current count

        Returns:
            Formatted progress counter string
        """
        
        return (
            f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}" 
            f"{str(current).rjust(self.number_width, '0')}"
            f"{Style.DIM}/{Style.RESET_ALL}{Fore.BLUE}"
            f"{str(self.total_count).rjust(self.number_width, '0')}"
            f"{Style.RESET_ALL}"
        )
    

    def placeholder(self, text: str = '') -> str:
        """
        Create a placeholder of appropriate width.
        
        Args:
            text: Text to display in the placeholder
            
        Returns:
            Formatted placeholder string
        """

        return (
            f"{Fore.LIGHTGREEN_EX}" 
            f"{text[:self.width].ljust(self.width)}"
            f"{Style.RESET_ALL}"
        )


def get_song_id_from_filename(filename: str) -> Optional[str]:
    """
    Extract YouTube ID from a filename's last brackets.
    
    Args:
        filename: String containing YouTube ID in brackets
        
    Returns:
        YouTube ID if found, None otherwise
    """

    pattern = r'^.*\[(?P<youtube_id>[^\]]+)\][^\]]*$'

    if match := re.match(pattern, str(filename)):
        return match.group('youtube_id')
    
    return None


def get_song_id_from_url(url: str) -> Optional[str]:
    """
    Extract YouTube ID from a YouTube URL.
    
    Args:
        url: YouTube URL containing video ID after '='
        
    Returns:
        YouTube ID if found, None otherwise
    """

    pattern = r'^.*=(?P<youtube_id>.+)$'

    if match := re.match(pattern, str(url)):
        return match.group('youtube_id')
    
    return None


def get_match_score(artist: str, title: str, keywords: str) -> float:
    """
    Calculate similarity score between song details and search keywords.
    
    Args:
        artist: Song artist name
        title: Song title
        keywords: Space-separated search terms

    Returns:
        Match score (0-100), higher means better match
    """

    # If no keywords are provided, return a perfect score
    if not keywords:
        return 100.0

    song_name = f'{artist.lower()} {title.lower()}'.strip()
    keyword_list = keywords.lower().split()
    
    score = 0.0
    penalty = 0
    keyword_acc = ''
    weight = len(keyword_list)
    weight_sum = sum(range(1, weight + 1))
    
    # Calculate score based on keyword presence and fuzzy matching
    for keyword in keyword_list:
        keyword_acc = f'{keyword_acc} {keyword}'.strip()  # Accumulate keywords
        
        if keyword in song_name:
            score += 100 * weight
        else:
            fuzzy_score = (
                fuzz.WRatio(keyword_acc, artist.lower()) +
                fuzz.WRatio(keyword_acc, title.lower()) +
                3 * fuzz.WRatio(keyword_acc, song_name)
            ) / 5
            
            if fuzzy_score < 100 - 10 * len(keyword_list):
                penalty += weight
            score += fuzzy_score * weight
            
        weight -= 1
    
    # Calculate aggressiveness penalty based on the number of keywords
    # The more keywords, the more severe the penalty
    # This ensures that the score is not too high for a large number 
    # of keywords compared to score obtained with fewer keywords
    aggressiveness_penalty = 50 * math.exp(-(math.log(2) / 3) * weight_sum)

    # Return final score
    return max(
        (score / weight_sum) - aggressiveness_penalty - (penalty * 10),
        0
    )


def natural_sort_key(key: str) -> tuple[str, str]:
    """
    Return a pair of keys (tuple) from given one,
    in order to perform a deterministic case-insensitive sorting 
    (e.g., get "Une Clé Avec Majusculse et Caractères Accentués" 
    sorted close to "une cle avec majuscules et caracteres accentues").
    
    Args:
        key: Key from which derivating deterministic naturel sort key pair

    Returns:
        Tuple of (normalized key, original key)
    """

    return slugify(str(key)).casefold(), str(key)


def prompt_user(question: str, options: list[str]) -> str:
    """
    Format choices to be displayed in a prompt.
    
    Args:
        question: Question to the user
        options: List of possible answers

    Returns:
        String of formatted options (e.g., "(yes/no/retry) ? ")
    """

    formatted_options = [
        f"{Fore.CYAN}{opt}{Fore.RESET}" for opt in options
    ]
    return input(
        f"{Style.BRIGHT}{Fore.WHITE}"
        f"{question}{Fore.RESET} " 
        f" ({'/'.join(formatted_options)}) ? "
    ).lower()


def check_and_display_song_selection_result(songs: list):
    """
    Display song selection result.
    
    Args:
        song: List of songs

    Returns:
        Formatted string
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


def format_song_display(song: any, counter: str) -> str:
    """
    Format song information for display.
    
    Args:
        song: Song object with artist, title, duration attributes
        counter: Song number in list (e.g., '03/07)

    Returns:
        Formatted string with song details
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
        song: any, 
        count_formatter: CountFormatter
    ) -> None:
    """
    Display detailed information about a song.

    Args:
        song: Song model containing song metadata
        count_formatter: Counter for formatting song number
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
