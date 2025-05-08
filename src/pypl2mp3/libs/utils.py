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
from colorama import Fore, Style
from slugify import slugify
from thefuzz import fuzz


def extract_youtube_id_from_filename(filename: str) -> Optional[str]:
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


def extract_youtube_id_from_url(url: str) -> Optional[str]:
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


def calculate_fuzzy_match_score(artist: str, title: str, keywords: str) -> float:
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
    stacked_keywords = ''
    weight = len(keyword_list)
    weight_sum = sum(range(1, weight + 1))
    
    # Calculate score based on keyword presence and fuzzy matching
    for keyword in keyword_list:
        stacked_keywords = f'{stacked_keywords} {keyword}'.strip()
        
        if keyword in song_name:
            score += 100 * weight
        else:
            fuzzy_score = (
                fuzz.WRatio(stacked_keywords, artist.lower()) +
                fuzz.WRatio(stacked_keywords, title.lower()) +
                3 * fuzz.WRatio(stacked_keywords, song_name)
            ) / 5
            
            if fuzzy_score < 100 - 10 * len(keyword_list):
                penalty += weight
            score += fuzzy_score * weight
            
        weight -= 1
    
    # Calculate aggressiveness penalty based on the number of keywords
    # The more keywords, the more severe the penalty
    # This ensures that the score is not too high for a large number of keywords
    # compared to score obtained with fewer keywords
    aggressiveness_penalty = 50 * math.exp(-(math.log(2) / 3) * weight_sum)

    # Calculate final score
    final_score = max((score / weight_sum) - aggressiveness_penalty - (penalty * 10), 0)
    
    # Return final score
    return final_score


def get_deterministic_sort_key(text: str) -> tuple[str, str]:
    """
    Create a deterministic sort key for case-insensitive sorting.
    
    Args:
        text: Text to create sort key from

    Returns:
        Tuple of (normalized text, original text)
    """

    return slugify(str(text)).casefold(), str(text)


def format_song_display(counter: str, song: any) -> str:
    """
    Format song information for display.
    
    Args:
        counter: Song number in list (e.g., '03/07)
        song: Song object with artist, title, duration attributes

    Returns:
        Formatted string with song details
    """

    junk_indicator = " (JUNK)" if song.has_junk_filename else ""
    
    return (
        f"{counter}  "
        f"{Fore.WHITE}{song.duration}  "
        f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}{song.artist}  "
        f"{Fore.LIGHTYELLOW_EX}{song.title}{Fore.MAGENTA}"
        f"{junk_indicator}{Fore.RESET}{Style.RESET_ALL}"
    )


@dataclass
class LabelFormatter:
    """
    Utility class for formatting text labels with consistent padding.
    """
    
    tab_size: int
    
    def format(self, label: str) -> str:
        """
        Format a label with consistent padding and styling.
        
        Args:
            label: Label text to format

        Returns:
            Formatted label string
        """
        return f"{Fore.WHITE}{Style.DIM}{label.ljust(self.tab_size)} {Style.RESET_ALL}"
    
    
    def format_raw(self, label: str) -> str:
        """
        Format a label with consistent padding but no styling.
        
        Args:
            label: Label text to format

        Returns:
            Formatted label string
        """
        return f"{label.ljust(self.tab_size)}"


@dataclass
class ProgressCounter:
    """
    Utility class for formatting progress counters.
    """
    
    total_count: int
    
    def __post_init__(self):
        self.number_width = max(2, len(str(self.total_count)))
        self.pad_size = self.number_width * 2 + 1
    
    def format(self, current: int) -> str:
        """
        Format a progress counter (e.g., '01/10').
        
        Args:
            current: Current count

        Returns:
            Formatted progress counter string
        """
        
        return (
            f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{str(current).rjust(self.number_width, '0')}"
            f"{Style.DIM}/{Style.RESET_ALL}"
            f"{Fore.GREEN}{str(self.total_count).rjust(self.number_width, '0')}"
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

        return f"{Fore.LIGHTGREEN_EX}{text[:self.pad_size].ljust(self.pad_size)}{Style.RESET_ALL}"
