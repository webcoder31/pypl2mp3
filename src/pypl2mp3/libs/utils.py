#!/usr/bin/env python3

"""
This file is part of PYPL2MP3 software, 
a YouTube playlist MP3 converter that can also shazam, tag and play songs.
PYPL2MP3: YouTube playlist MP3 converter with Shazam integration and tagging capabilities.

@author    Thierry Thiers <webcoder31@gmail.com>
@copyright 2024 © Thierry Thiers <webcoder31@gmail.com>
@license   http://www.cecill.info  CeCILL-C License
@link      https://github.com/webcoder31/pypl2mp3

This module provides utility functions for YouTube ID extraction, match score calculation,
string matching and formatting operations.
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
    """Extract YouTube ID from a filename's last brackets.
    
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
    """Extract YouTube ID from a YouTube URL.
    
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
    """Calculate similarity score between song details and search keywords.
    
    Args:
        artist: Song artist name
        title: Song title
        keywords: Space-separated search terms
        
    Returns:
        Match score (0-100), higher means better match
    """
    if not keywords:
        return 100.0

    song_name = f'{artist.lower()} {title.lower()}'.strip()
    keyword_list = keywords.lower().split()
    
    score = 0.0
    penalty = 0
    stacked_keywords = ''
    weight = len(keyword_list)
    weight_sum = sum(range(1, weight + 1))
    
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
    
    severity_factor = 50 * math.exp(-(math.log(2) / 3) * weight_sum)
    final_score = max((score / weight_sum) - severity_factor - (penalty * 10), 0)
    
    return final_score


def get_deterministic_sort_key(text: str) -> tuple[str, str]:
    """Create a deterministic sort key for case-insensitive sorting.
    
    Args:
        text: Text to create sort key from
        
    Returns:
        Tuple of (normalized text, original text)
    """
    return slugify(str(text)).casefold(), str(text)


def format_song_display(counter: int, song) -> str:
    """Format song information for display.
    
    Args:
        counter: Song number in list
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
    """Utility class for formatting text labels with consistent padding."""
    
    tab_size: int
    
    def format(self, label: str) -> str:
        """Format a label with consistent padding and styling.
        
        Args:
            label: Label text to format
        Returns:
            Formatted label string
        """
        return f"{Fore.WHITE}{Style.DIM}{label.ljust(self.tab_size)} {Style.RESET_ALL}"


@dataclass
class ProgressCounter:
    """Utility class for formatting progress counters."""
    
    total_count: int
    
    def __post_init__(self):
        self.number_width = max(2, len(str(self.total_count)))
        self.pad_size = self.number_width * 2 + 1
    
    def format(self, current: int) -> str:
        """Format a progress counter (e.g., '01/10').
        
        Args:
            current: Current count
        Returns:
            Formatted progress counter string
        """
        return (
            f"{Fore.LIGHTGREEN_EX}{str(current).rjust(self.number_width, '0')}"
            f"{Fore.WHITE}{Style.DIM}/{Style.RESET_ALL}"
            f"{Fore.LIGHTGREEN_EX}{str(self.total_count).rjust(self.number_width, '0')}"
            f"{Style.RESET_ALL}"
        )
    
    def placeholder(self, text: str = '') -> str:
        """Create a placeholder of appropriate width.
        
        Args:
            text: Text to display in the placeholder
        Returns:
            Formatted placeholder string
        """
        return f"{Fore.LIGHTGREEN_EX}{text[:self.pad_size].ljust(self.pad_size)}{Style.RESET_ALL}"
